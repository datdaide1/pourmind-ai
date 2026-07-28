import uuid
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import update

from app.db.postgres import AsyncSessionLocal
from app.db.models import Conversation, Message, User
from sqlalchemy.exc import SQLAlchemyError
from app.agents.graph import graph
from app.agents.state import AgentState
from app.tools.cost_abv_calculator import calculate_cost_and_abv
from app.tools.qdrant_retriever import get_relevant_cocktails, get_relevant_venues
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

logger = logging.getLogger(__name__)

router = APIRouter()

# Helper function to safely parse UUIDs
def parse_uuid(val: Any) -> Optional[uuid.UUID]:
    if not val:
        return None
    if isinstance(val, uuid.UUID):
        return val
    val_str = str(val).strip().lower()
    if val_str in ("null", "none", ""):
        return None
    try:
        return uuid.UUID(val_str)
    except ValueError:
        return None

# Pydantic Schemas for Payloads
class SessionInitPayload(BaseModel):
    user_id: Optional[str] = None
    guest_session_id: str = Field(..., max_length=255)
    mode: str = "guest"  # "guest" or "bartender"

class LocationContext(BaseModel):
    lat: float
    lng: float

class ChatContext(BaseModel):
    current_location: Optional[LocationContext] = None

class ChatMessagePayload(BaseModel):
    session_id: str
    content: str
    context: Optional[ChatContext] = None

class RecipeIngredient(BaseModel):
    ingredient: str
    amount_ml: float = Field(..., gt=0)

class CalculateCostPayload(BaseModel):
    recipe: List[RecipeIngredient]

class MigrateSessionPayload(BaseModel):
    guest_session_id: str
    user_id: str

# Endpoints
@router.post("/session/init")
async def session_init(payload: SessionInitPayload):
    parsed_user_id = parse_uuid(payload.user_id)
    
    async with AsyncSessionLocal() as db_session:
        if parsed_user_id is not None:
            user_stmt = select(User).where(User.id == parsed_user_id)
            user_result = await db_session.execute(user_stmt)
            user_exists = user_result.scalar_one_or_none()
            if not user_exists:
                raise HTTPException(status_code=400, detail="User does not exist")

        try:
            stmt = select(Conversation).where(
                Conversation.session_id == payload.guest_session_id,
                Conversation.is_deleted == False
            )
            result = await db_session.execute(stmt)
            conv = result.scalar_one_or_none()
            
            if not conv:
                conv = Conversation(
                    session_id=payload.guest_session_id,
                    user_id=parsed_user_id,
                    title="Guest Chat" if payload.mode == "guest" else "Bartender Chat",
                    metadata_={"mode": payload.mode}
                )
                db_session.add(conv)
                await db_session.commit()
                logger.info(f"Created new conversation for guest_session_id: {payload.guest_session_id}")
            else:
                # Update user_id if it was null and a valid user_id is provided now
                if conv.user_id is None and parsed_user_id is not None:
                    conv.user_id = parsed_user_id
                    await db_session.commit()
                    logger.info(f"Updated conversation user_id to: {parsed_user_id}")
        except SQLAlchemyError as e:
            await db_session.rollback()
            logger.error(f"Database error during session init: {e}")
            raise HTTPException(status_code=400, detail="Database constraint violation or error")

    if payload.mode == "bartender":
        welcome_message = "Welcome, Master Bartender. I can help you calculate cocktail costs, ABV, and profit margins. How can I assist you today?"
        suggested_prompts = ["Calculate cost of Martini", "Calculate margin for Gin Tonic"]
    else:
        welcome_message = "Chào buổi tối, The Mixologist đã sẵn sàng phục vụ bạn..."
        suggested_prompts = ["Gợi ý quán đi Date", "Tôi muốn uống vị chua"]
        
    async with AsyncSessionLocal() as db_session:
        try:
            stmt = select(Conversation).where(
                Conversation.session_id == payload.guest_session_id,
                Conversation.is_deleted == False
            ).options(selectinload(Conversation.messages))
            result = await db_session.execute(stmt)
            conv = result.scalar_one_or_none()
            if conv and len(conv.messages) == 0:
                welcome_msg_db = Message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=welcome_message,
                    ui_blocks=[{"type": "quick_replies", "replies": suggested_prompts}]
                )
                db_session.add(welcome_msg_db)
                await db_session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Error saving welcome message: {e}")

    return {
        "session_id": payload.guest_session_id,
        "welcome_message": welcome_message,
        "suggested_prompts": suggested_prompts
    }

@router.post("/chat/message")
async def chat_message(payload: ChatMessagePayload):
    async def event_generator():
        # 1. Retrieve history from database
        async with AsyncSessionLocal() as db_session:
            stmt = select(Conversation).where(
                Conversation.session_id == payload.session_id,
                Conversation.is_deleted == False
            ).options(selectinload(Conversation.messages))
            result = await db_session.execute(stmt)
            db_conv = result.scalar_one_or_none()
            
            if not db_conv:
                # Create a conversation record on the fly if it does not exist
                db_conv = Conversation(
                    session_id=payload.session_id,
                    title="Chat Session"
                )
                db_session.add(db_conv)
                await db_session.flush()
                conv_id = db_conv.id
                history_messages = []
            else:
                conv_id = db_conv.id
                db_messages = sorted(db_conv.messages, key=lambda m: m.created_at)
                history_messages = []
                for m in db_messages:
                    if m.role == "user":
                        history_messages.append(HumanMessage(content=m.content))
                    elif m.role == "assistant":
                        history_messages.append(AIMessage(content=m.content))

        # 2. Setup graph state
        new_user_message = HumanMessage(content=payload.content)
        state = AgentState(
            messages=history_messages + [new_user_message],
            intent=None,
            customer_age=None,
            allergies=[],
            safety_status="safe",
            context="",
            tool_called=False
        )

        # 3. Stream from LangGraph
        final_text_accum = []
        final_state = None

        try:
            async for event in graph.astream_events(state, version="v2"):
                kind = event.get("event")
                if kind == "on_chat_model_stream":
                    # Filter out streaming from router node (which outputs raw JSON)
                    node_name = event.get("metadata", {}).get("langgraph_node")
                    if node_name not in ["b2c_mixologist", "b2b_bartender"]:
                        continue
                        
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        if isinstance(token, list):
                            token = "".join(item.get("text", "") for item in token if isinstance(item, dict) and "text" in item)
                        if isinstance(token, str) and token:
                            final_text_accum.append(token)
                            yield f"data: {json.dumps({'token': token})}\n\n"
                elif kind == "on_chain_end":
                    if not event.get("parent_ids"):
                        final_state = event["data"].get("output")
        except Exception as e:
            logger.error(f"Error during LangGraph streaming: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        final_text = "".join(final_text_accum)

        # Fallback if streaming output was empty
        if final_state and "messages" in final_state and len(final_state["messages"]) > 0:
            last_msg = final_state["messages"][-1]
            if not final_text and hasattr(last_msg, "content"):
                if isinstance(last_msg.content, list):
                    final_text = "".join(item.get("text", "") for item in last_msg.content if isinstance(item, dict) and "text" in item)
                else:
                    final_text = last_msg.content

        if not final_text:
            final_text = "I'm sorry, I could not generate a response."

        # 4. Construct SDUI Blocks
        intent = "b2c"
        tool_result = None

        if final_state:
            intent = final_state.get("intent") or "b2c"
            # Extract tool call outputs
            for msg in final_state.get("messages", []):
                if isinstance(msg, ToolMessage) and msg.name == "calculate_cost_tool":
                    try:
                        tool_result = json.loads(msg.content)
                    except Exception:
                        pass

        venues = []
        cocktails = []
        if intent == "b2c":
            try:
                venues = await get_relevant_venues(payload.content, limit=2)
                cocktails = await get_relevant_cocktails(payload.content, limit=2)
            except Exception as e:
                logger.error(f"Error fetching RAG context: {e}")

        ui_blocks = []

        if intent == "b2b":
            if tool_result:
                recipe_ingredients = [
                    {
                        "name": item["name"],
                        "amount": f"{item['volume_ml']}ml",
                        "cost_vnd": item["cost"]
                    }
                    for item in tool_result.get("breakdown", [])
                ]
                total_cost = tool_result.get("total_cost_vnd", 0.0)
                suggested_price = total_cost * 5.0  # Assumes 80% margin target

                ui_blocks.append({
                    "type": "recipe_matrix",
                    "recipe_name": "Calculated Recipe",
                    "ingredients": recipe_ingredients,
                    "financials": {
                        "total_cost_vnd": total_cost,
                        "suggested_price_vnd": suggested_price,
                        "margin_percent": 80.0,
                        "abv_percent": tool_result.get("abv", 0.0)
                    },
                    "rationale": "Calculated based on standard cost and ABV parameters."
                })

                ui_blocks.append({
                    "type": "cost_summary",
                    "total_cost_vnd": total_cost,
                    "total_volume_ml": tool_result.get("total_volume_ml", 0.0),
                    "estimated_abv": tool_result.get("abv", 0.0)
                })
            else:
                ui_blocks.append({
                    "type": "rationale",
                    "content": "B2B financial analysis for cocktail menu planning."
                })
            quick_replies = ["Calculate another recipe", "Show pricing history"]
        else:
            if venues:
                items = []
                for v in venues:
                    items.append({
                        "name": v.get("name", "Unknown Venue"),
                        "address": v.get("address", ""),
                        "district": v.get("district", ""),
                        "city": v.get("city", ""),
                        "rating": v.get("rating", 0.0),
                        "rationale": v.get("rationale") or f"✨ Recommended venue with rating {v.get('rating', 'N/A')}."
                    })
                ui_blocks.append({
                    "type": "carousel_venues",
                    "items": items
                })

            if cocktails:
                items = []
                for c in cocktails:
                    items.append({
                        "name": c.get("name", "Unknown Cocktail"),
                        "alcoholic_type": c.get("alcoholic_type", ""),
                        "base_liquor": c.get("base_liquor", ""),
                        "ingredients": c.get("ingredients", ""),
                        "instructions": c.get("instructions", ""),
                        "rationale": c.get("rationale") or f"✨ Recommended drink: {c.get('alcoholic_type', 'Cocktail')}."
                    })
                ui_blocks.append({
                    "type": "carousel_cocktails",
                    "items": items
                })

            ui_blocks.append({
                "type": "rationale",
                "content": "Recommendations tailored to flavor preferences and top-rated venues."
            })
            
        # Dynamically generate quick replies based on final text
        quick_replies = []
        if final_text and len(final_text) > 20:
            try:
                from app.agents.nodes import llm
                qr_prompt = f"Based on this AI response, suggest 2 very short quick replies (max 6 words each) in Vietnamese for the user to click to continue the conversation. Return ONLY a valid JSON array of strings, e.g. [\"Tư vấn thêm\", \"Giá bao nhiêu\"]. No other text. \n\nAI Response: {final_text[-500:]}"
                qr_resp = await llm.ainvoke([HumanMessage(content=qr_prompt)])
                clean_json = qr_resp.content.strip().strip("`").removeprefix("json").strip()
                quick_replies = json.loads(clean_json)
                if not isinstance(quick_replies, list):
                    quick_replies = []
            except Exception as e:
                logger.error(f"Failed to generate quick replies: {e}")

        if quick_replies:
            ui_blocks.append({
                "type": "quick_replies",
                "replies": quick_replies
            })

        # Yield the final message containing the constructed SDUI blocks
        yield f"data: {json.dumps({'ui_blocks': ui_blocks, 'quick_replies': quick_replies, 'done': True})}\n\n"

        # 5. Save the user and assistant messages (with ui_blocks JSON) to the database
        try:
            async with AsyncSessionLocal() as db_session:
                user_msg = Message(
                    conversation_id=conv_id,
                    role="user",
                    content=payload.content
                )
                assistant_msg = Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content=final_text,
                    ui_blocks=ui_blocks
                )
                db_session.add_all([user_msg, assistant_msg])
                await db_session.commit()
                logger.info("Successfully persisted conversation messages.")
        except Exception as e:
            logger.error(f"Error persisting messages: {e}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/tools/calculate_cost")
async def calculate_cost_endpoint(payload: CalculateCostPayload):
    try:
        recipe_mapped = [
            {
                "name": item.ingredient,
                "volume_ml": item.amount_ml
            }
            for item in payload.recipe
        ]
        res = await calculate_cost_and_abv(recipe_mapped)
        return {
            "total_cost_vnd": res["total_cost_vnd"],
            "total_volume_ml": res["total_volume_ml"],
            "estimated_abv": res["abv"]
        }
    except Exception as e:
        logger.error(f"Error calculating recipe cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/conversations")
async def get_user_conversations(user_id: str):
    parsed_user_id = parse_uuid(user_id)
    if not parsed_user_id:
        return {"conversations": []}

    try:
        async with AsyncSessionLocal() as db_session:
            stmt = select(Conversation).where(
                Conversation.user_id == parsed_user_id,
                Conversation.is_deleted == False
            ).order_by(Conversation.created_at.desc())
            result = await db_session.execute(stmt)
            conversations = result.scalars().all()
            
            return {
                "conversations": [
                    {
                        "session_id": conv.session_id,
                        "title": conv.title,
                        "created_at": conv.created_at.isoformat()
                    }
                    for conv in conversations
                ]
            }
    except Exception as e:
        logger.error(f"Error getting user conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/history")
async def get_chat_messages(session_id: str):
    # In frontend, we called /api/v1/chat/history?session_id=...
    # Return messages for the session
    try:
        async with AsyncSessionLocal() as db_session:
            stmt = select(Message).join(Conversation).where(
                Conversation.session_id == session_id
            ).order_by(Message.created_at.asc())
            result = await db_session.execute(stmt)
            messages = result.scalars().all()
            
            return {
                "messages": [
                    {
                        "id": str(msg.id),
                        "role": msg.role,
                        "content": msg.content,
                        "ui_blocks": msg.ui_blocks,
                        "created_at": msg.created_at.isoformat()
                    }
                    for msg in messages
                ]
            }
    except Exception as e:
        logger.error(f"Error getting chat messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/chat/{session_id}")
async def delete_chat_session(session_id: str):
    try:
        async with AsyncSessionLocal() as db_session:
            stmt = update(Conversation).where(
                Conversation.session_id == session_id
            ).values(is_deleted=True)
            result = await db_session.execute(stmt)
            await db_session.commit()
            
            # Check row count updated if supported, or verify by returning success
            return {
                "success": True,
                "message": "Chat deleted"
            }
    except Exception as e:
        logger.error(f"Error deleting chat session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_items(query: str = "", type: str = "cocktail", limit: int = 10):
    from app.tools.qdrant_retriever import get_relevant_cocktails, get_relevant_venues
    try:
        if type == "cocktail":
            results = await get_relevant_cocktails(query, limit=limit)
        elif type == "venue":
            results = await get_relevant_venues(query, limit=limit)
        else:
            raise HTTPException(status_code=400, detail="Invalid type. Must be 'cocktail' or 'venue'")
        return {"results": results}
    except Exception as e:
        logger.error(f"Search API Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during search")

@router.post("/session/migrate")
async def session_migrate(payload: MigrateSessionPayload):
    parsed_user_id = parse_uuid(payload.user_id)
    if not parsed_user_id:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    async with AsyncSessionLocal() as db_session:
        user_stmt = select(User).where(User.id == parsed_user_id)
        user_result = await db_session.execute(user_stmt)
        user_exists = user_result.scalar_one_or_none()
        if not user_exists:
            raise HTTPException(status_code=400, detail="User does not exist")

        try:
            stmt = update(Conversation).where(
                Conversation.session_id == payload.guest_session_id
            ).values(user_id=parsed_user_id)
            await db_session.execute(stmt)
            await db_session.commit()
        except SQLAlchemyError as e:
            await db_session.rollback()
            logger.error(f"Error migrating guest session {payload.guest_session_id}: {e}")
            raise HTTPException(status_code=400, detail="Database constraint violation or error")
            
    return {
        "success": True,
        "message": "Conversations migrated successfully"
    }
