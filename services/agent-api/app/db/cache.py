import json
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from app.db.redis import redis_client
from app.db.postgres import AsyncSessionLocal
from app.db.models import LiquorPrice, MixologyRule, Ingredient

logger = logging.getLogger(__name__)

CACHE_TTL = 3600  # TTL in seconds (1 hour)

async def get_liquor_price_by_name(name: str, session=None) -> List[Dict[str, Any]]:
    """
    Retrieves liquor prices by name, checking Upstash Redis cache first.
    If not cached, queries PostgreSQL, caches the result, and returns it.
    """
    cache_key = f"liquor_price:name:{name}"
    
    # Try cache first
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for key: {cache_key}")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Redis cache read failed for key {cache_key}: {e}")
    
    # Cache miss
    logger.info(f"Cache miss for key: {cache_key}. Querying Supabase...")
    
    is_local_session = False
    if session is None:
        session = AsyncSessionLocal()
        is_local_session = True
        
    try:
        stmt = select(LiquorPrice).where(LiquorPrice.name == name)
        result = await session.execute(stmt)
        records = result.scalars().all()
        
        # Serialize to dict list
        serialized = [
            {
                "id": record.id,
                "name": record.name,
                "category": record.category,
                "size_raw": record.size_raw,
                "size_ml": record.size_ml,
                "price_vnd": record.price_vnd,
                "price_per_ml_vnd": record.price_per_ml_vnd
            }
            for record in records
        ]
        
        # Cache the serialized value in Redis
        try:
            await redis_client.setex(cache_key, CACHE_TTL, json.dumps(serialized))
            logger.info(f"Successfully cached key: {cache_key}")
        except Exception as e:
            logger.warning(f"Redis cache write failed for key {cache_key}: {e}")
            
        return serialized
    finally:
        if is_local_session:
            await session.close()

async def get_liquor_prices_by_category(category: str, session=None) -> List[Dict[str, Any]]:
    """
    Retrieves liquor prices by category, checking Upstash Redis cache first.
    If not cached, queries PostgreSQL, caches the result, and returns it.
    """
    cache_key = f"liquor_prices:category:{category}"
    
    # Try cache first
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for key: {cache_key}")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Redis cache read failed for key {cache_key}: {e}")
        
    # Cache miss
    logger.info(f"Cache miss for key: {cache_key}. Querying Supabase...")
    
    is_local_session = False
    if session is None:
        session = AsyncSessionLocal()
        is_local_session = True
        
    try:
        stmt = select(LiquorPrice).where(LiquorPrice.category == category)
        result = await session.execute(stmt)
        records = result.scalars().all()
        
        serialized = [
            {
                "id": record.id,
                "name": record.name,
                "category": record.category,
                "size_raw": record.size_raw,
                "size_ml": record.size_ml,
                "price_vnd": record.price_vnd,
                "price_per_ml_vnd": record.price_per_ml_vnd
            }
            for record in records
        ]
        
        try:
            await redis_client.setex(cache_key, CACHE_TTL, json.dumps(serialized))
            logger.info(f"Successfully cached key: {cache_key}")
        except Exception as e:
            logger.warning(f"Redis cache write failed for key {cache_key}: {e}")
            
        return serialized
    finally:
        if is_local_session:
            await session.close()

async def get_mixology_rule_by_ingredient(ingredient: str, session=None) -> Optional[Dict[str, Any]]:
    """
    Retrieves mixology rules by ingredient name, checking Upstash Redis cache first.
    If not cached, queries PostgreSQL, caches the result, and returns it.
    """
    cache_key = f"mixology_rule:ingredient:{ingredient}"
    
    # Try cache first
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for key: {cache_key}")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Redis cache read failed for key {cache_key}: {e}")
        
    # Cache miss
    logger.info(f"Cache miss for key: {cache_key}. Querying Supabase...")
    
    is_local_session = False
    if session is None:
        session = AsyncSessionLocal()
        is_local_session = True
        
    try:
        stmt = select(MixologyRule).where(MixologyRule.ingredient == ingredient)
        result = await session.execute(stmt)
        record = result.scalars().first()
        
        if not record:
            return None
            
        serialized = {
            "id": record.id,
            "ingredient": record.ingredient,
            "substitutes": record.substitutes,
            "notes": record.notes
        }
        
        try:
            await redis_client.setex(cache_key, CACHE_TTL, json.dumps(serialized))
            logger.info(f"Successfully cached key: {cache_key}")
        except Exception as e:
            logger.warning(f"Redis cache write failed for key {cache_key}: {e}")
            
        return serialized
    finally:
        if is_local_session:
            await session.close()


async def get_ingredient_by_name(name: str, session=None) -> Optional[Dict[str, Any]]:
    """
    Retrieves ingredient by name (case-insensitive, stripped), checking Redis cache first.
    If not cached, queries PostgreSQL, caches the result, and returns it.
    Supports partial match fallbacks.
    """
    clean_name = name.strip()
    normalized_name = clean_name.lower()
    cache_key = f"ingredient:name_ci:{normalized_name}"
    
    # Try cache first
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for key: {cache_key}")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Redis cache read failed for key {cache_key}: {e}")
        
    # Cache miss
    logger.info(f"Cache miss for key: {cache_key}. Querying Supabase...")
    
    is_local_session = False
    if session is None:
        session = AsyncSessionLocal()
        is_local_session = True
        
    try:
        from sqlalchemy import func
        # 1. Exact case-insensitive match
        stmt = select(Ingredient).where(func.lower(Ingredient.name) == normalized_name)
        result = await session.execute(stmt)
        record = result.scalars().first()
        
        # 2. If not found, try partial match (normalized_name is in Ingredient.name)
        if not record:
            stmt = select(Ingredient).where(Ingredient.name.ilike(f"%{clean_name}%"))
            result = await session.execute(stmt)
            record = result.scalars().first()
            
        # 3. If still not found, try reverse partial match (Ingredient.name is in clean_name)
        if not record:
            stmt = select(Ingredient)
            result = await session.execute(stmt)
            all_records = result.scalars().all()
            for rec in all_records:
                if rec.name.lower() in normalized_name or normalized_name in rec.name.lower():
                    record = rec
                    break
                    
        if not record:
            return None
            
        serialized = {
            "id": record.id,
            "name": record.name,
            "description": record.description,
            "type": record.type,
            "is_alcoholic": record.is_alcoholic,
            "abv": record.abv
        }
        
        try:
            await redis_client.setex(cache_key, CACHE_TTL, json.dumps(serialized))
            logger.info(f"Successfully cached key: {cache_key}")
        except Exception as e:
            logger.warning(f"Redis cache write failed for key {cache_key}: {e}")
            
        return serialized
    finally:
        if is_local_session:
            await session.close()


async def get_liquor_price_by_name_case_insensitive(name: str, session=None) -> List[Dict[str, Any]]:
    """
    Retrieves liquor prices by name (case-insensitive, stripped), checking Redis cache first.
    If not cached, queries PostgreSQL, caches the result, and returns it.
    Supports partial match fallbacks.
    """
    clean_name = name.strip()
    normalized_name = clean_name.lower()
    cache_key = f"liquor_price:name_ci:{normalized_name}"
    
    # Try cache first
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for key: {cache_key}")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Redis cache read failed for key {cache_key}: {e}")
        
    # Cache miss
    logger.info(f"Cache miss for key: {cache_key}. Querying Supabase...")
    
    is_local_session = False
    if session is None:
        session = AsyncSessionLocal()
        is_local_session = True
        
    try:
        from sqlalchemy import func
        # 1. Exact case-insensitive match
        stmt = select(LiquorPrice).where(func.lower(LiquorPrice.name) == normalized_name)
        result = await session.execute(stmt)
        records = result.scalars().all()
        
        # 2. If not found, try partial match (normalized_name is in LiquorPrice.name)
        if not records:
            stmt = select(LiquorPrice).where(LiquorPrice.name.ilike(f"%{clean_name}%"))
            result = await session.execute(stmt)
            records = result.scalars().all()
            
        # 3. If still not found, try reverse partial match (LiquorPrice.name is in clean_name)
        if not records:
            stmt = select(LiquorPrice)
            result = await session.execute(stmt)
            all_records = result.scalars().all()
            matched_records = []
            for record in all_records:
                if record.name.lower() in normalized_name or normalized_name in record.name.lower():
                    matched_records.append(record)
            if matched_records:
                records = matched_records
                
        # Serialize to dict list
        serialized = [
            {
                "id": record.id,
                "name": record.name,
                "category": record.category,
                "size_raw": record.size_raw,
                "size_ml": record.size_ml,
                "price_vnd": record.price_vnd,
                "price_per_ml_vnd": record.price_per_ml_vnd
            }
            for record in records
        ]
        
        # Cache the serialized value in Redis
        try:
            await redis_client.setex(cache_key, CACHE_TTL, json.dumps(serialized))
            logger.info(f"Successfully cached key: {cache_key}")
        except Exception as e:
            logger.warning(f"Redis cache write failed for key {cache_key}: {e}")
            
        return serialized
    finally:
        if is_local_session:
            await session.close()


async def get_mixology_rule_by_ingredient_case_insensitive(ingredient: str, session=None) -> Optional[Dict[str, Any]]:
    """
    Retrieves mixology rules by ingredient name (case-insensitive, stripped), checking Redis cache first.
    If not cached, queries PostgreSQL, caches the result, and returns it.
    Supports partial match fallbacks.
    """
    clean_name = ingredient.strip()
    normalized_name = clean_name.lower()
    cache_key = f"mixology_rule:ingredient_ci:{normalized_name}"
    
    # Try cache first
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for key: {cache_key}")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Redis cache read failed for key {cache_key}: {e}")
        
    # Cache miss
    logger.info(f"Cache miss for key: {cache_key}. Querying Supabase...")
    
    is_local_session = False
    if session is None:
        session = AsyncSessionLocal()
        is_local_session = True
        
    try:
        from sqlalchemy import func
        # 1. Exact case-insensitive match
        stmt = select(MixologyRule).where(func.lower(MixologyRule.ingredient) == normalized_name)
        result = await session.execute(stmt)
        record = result.scalars().first()
        
        # 2. If not found, try partial match (normalized_name is in MixologyRule.ingredient)
        if not record:
            stmt = select(MixologyRule).where(MixologyRule.ingredient.ilike(f"%{clean_name}%"))
            result = await session.execute(stmt)
            record = result.scalars().first()
            
        # 3. If still not found, try reverse partial match (MixologyRule.ingredient is in clean_name)
        if not record:
            stmt = select(MixologyRule)
            result = await session.execute(stmt)
            all_records = result.scalars().all()
            for rec in all_records:
                if rec.ingredient.lower() in normalized_name or normalized_name in rec.ingredient.lower():
                    record = rec
                    break
                    
        if not record:
            return None
            
        serialized = {
            "id": record.id,
            "ingredient": record.ingredient,
            "substitutes": record.substitutes,
            "notes": record.notes
        }
        
        try:
            await redis_client.setex(cache_key, CACHE_TTL, json.dumps(serialized))
            logger.info(f"Successfully cached key: {cache_key}")
        except Exception as e:
            logger.warning(f"Redis cache write failed for key {cache_key}: {e}")
            
        return serialized
    finally:
        if is_local_session:
            await session.close()

