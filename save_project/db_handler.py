import psycopg2
import psycopg2.extras
import logging
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# support UTF-8 BOM in .env files
load_dotenv(encoding='utf-8-sig')

class DatabaseHandler:
    def __init__(self):
        self.conn: Optional[psycopg2.extensions.connection] = None
        self._schema_initialized = False
        self.host = os.getenv("DB_HOST", "")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.database = os.getenv("DB_NAME", "defaultdb")
        self.user = os.getenv("DB_USER", "")
        self.password = os.getenv("DB_PASSWORD", "")
        self.ssl_mode = os.getenv("DB_SSL_MODE", "require")
        # debug: log connection parameters (hide password)
        logger.debug("DB connection params: host=%s port=%s db=%s user=%s sslmode=%s",
                     self.host, self.port, self.database, self.user, self.ssl_mode)
    
    async def connect(self):
        """Create database connection"""
        if self.conn is not None:
            return
        
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                sslmode=self.ssl_mode
            )
            self.conn.autocommit = True
            logger.info("Connected to PostgreSQL database")
            await self.initialize_schema()
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self._schema_initialized = False
            logger.info("Disconnected from database")
    
    async def initialize_schema(self):
        """Create tables if they don't exist"""
        if self._schema_initialized:
            return
        with self.conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS project_details (
                    project_id VARCHAR(50) PRIMARY KEY,
                    detail_result JSONB NOT NULL,
                    http_status INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_project_details_project_id ON project_details(project_id)')
            self._schema_initialized = True
            logger.info("Database schema initialized")
    
    async def save_project_detail_result(
        self, project_id: str, detail_result: Dict[str, Any], http_status: Optional[int] = None
    ):
        """Save only the raw project detail result (projectForSlider) as JSON."""
        await self.initialize_schema()
        payload = dict(detail_result) if isinstance(detail_result, dict) else {}
        payload.pop('_http_status', None)
        with self.conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO project_details (project_id, detail_result, http_status)
                VALUES (%s, %s, %s)
                ON CONFLICT (project_id) DO UPDATE SET
                    detail_result = EXCLUDED.detail_result,
                    http_status = EXCLUDED.http_status,
                    updated_at = CURRENT_TIMESTAMP
                ''',
                (str(project_id)[:50], psycopg2.extras.Json(payload), http_status),
            )


# Global database handler instance
_db_handler: Optional[DatabaseHandler] = None


async def get_db_handler() -> DatabaseHandler:
    """Get or create the global database handler instance"""
    global _db_handler
    if _db_handler is None:
        _db_handler = DatabaseHandler()
        await _db_handler.connect()
    return _db_handler


async def close_db_handler():
    """Close the global database handler"""
    global _db_handler
    if _db_handler is not None:
        await _db_handler.disconnect()
        _db_handler = None
