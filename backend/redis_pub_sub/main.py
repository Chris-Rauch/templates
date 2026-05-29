import asyncio
import json
from typing import Any, Callable, Dict, Optional
import redis.asyncio as redis
from dotenv import load_dotenv
import os
# from src.util.logging_config import logger
import logging


load_dotenv()
BROKER = os.getenv("BROKER")
LOG_LEVEL = os.getenv("LOG_LEVEL")

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedisPubSub:
    """Redis Pub/Sub manager for async operations."""
    
    def __init__(self, redis_url: str = BROKER):
        """
        Initialize Redis pub/sub connection.
        
        :param redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.subscribers: Dict[str, list[Callable]] = {}
        self._listener_task: Optional[asyncio.Task] = None
        
    async def connect(self):
        """Establish Redis connection."""
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()
            logger.info("Redis pub/sub connected")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.aclose()
        if self.redis_client:
            await self.redis_client.aclose()
        logger.info("Redis pub/sub disconnected")
    
    async def publish(self, channel: str, message: Any):
        """
        Publish a message to a channel.
        
        :param channel: Channel name
        :param message: Message to publish (will be JSON serialized)
        """
        if not self.redis_client:
            logger.warning("Redis not connected, cannot publish")
            return False
        
        try:
            # Serialize message to JSON
            if not isinstance(message, str):
                message = json.dumps(message)
            
            await self.redis_client.publish(channel, message)
            logger.debug(f"Published to {channel}: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            return False
    
    async def subscribe(self, channel: str, callback: Callable):
        """
        Subscribe to a channel with a callback function.
        
        :param channel: Channel name
        :param callback: Async function to call when message received
        """
        if not self.pubsub:
            logger.error("Pubsub not initialized")
            return False
        
        try:
            # Add callback to subscribers
            if channel not in self.subscribers:
                self.subscribers[channel] = []
                await self.pubsub.subscribe(channel)
                logger.info(f"Subscribed to channel: {channel}")
            
            self.subscribers[channel].append(callback)
            
            # Start listener if not already running
            if not self._listener_task or self._listener_task.done():
                self._listener_task = asyncio.create_task(self._listen())
            
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            return False
    
    async def unsubscribe(self, channel: str, callback: Optional[Callable] = None):
        """
        Unsubscribe from a channel.
        
        :param channel: Channel name
        :param callback: Specific callback to remove (if None, removes all)
        """
        if channel not in self.subscribers:
            return
        
        if callback:
            # Remove specific callback
            if callback in self.subscribers[channel]:
                self.subscribers[channel].remove(callback)
        else:
            # Remove all callbacks
            self.subscribers[channel] = []
        
        # Unsubscribe from channel if no more callbacks
        if not self.subscribers[channel]:
            del self.subscribers[channel]
            if self.pubsub:
                await self.pubsub.unsubscribe(channel)
                logger.info(f"Unsubscribed from channel: {channel}")
    
    async def _listen(self):
        """Internal method to listen for messages."""
        if not self.pubsub:
            return
        
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]
                    
                    # Try to parse JSON
                    try:
                        data = json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        pass  # Keep as string if not JSON
                    
                    # Call all callbacks for this channel
                    if channel in self.subscribers:
                        for callback in self.subscribers[channel]:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(data)
                                else:
                                    callback(data)
                            except Exception as e:
                                logger.error(f"Error in callback for {channel}: {e}")
        except asyncio.CancelledError:
            logger.info("Listener task cancelled")
        except Exception as e:
            logger.error(f"Error in listener: {e}")


# Usage example
async def main():
    # Initialize pub/sub
    pubsub = RedisPubSub(BROKER)
    await pubsub.connect()
    
    # Define a subscriber callback
    async def handle_message(message):
        print(f"Received: {message}")
    
    # Subscribe to a channel
    await pubsub.subscribe("notifications", handle_message)
    
    # Publish some messages
    await pubsub.publish("notifications", {"event": "user_login", "user_id": 123})
    await pubsub.publish("notifications", {"event": "user_logout", "user_id": 123})
    
    # Keep running to receive messages
    await asyncio.sleep(5)
    
    # Cleanup
    await pubsub.disconnect()


if __name__ == "__main__":
    asyncio.run(main())