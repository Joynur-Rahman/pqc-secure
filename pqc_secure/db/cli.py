"""Database CLI utilities for initialization and management"""
import sys
import logging
from pqc_secure.db.init_db import (
    init_db,
    drop_all_tables,
    is_database_initialized,
    get_table_count,
    seed_demo_data,
    verify_database_health,
    clear_audit_logs,
    get_migration_status,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_usage():
    """Print CLI usage information"""
    print("""
PQC-Secure Database CLI

Usage:
    python -m pqc_secure.db.cli <command>

Commands:
    init                - Initialize database (run Alembic migrations)
    health              - Check database health
    status              - Show database initialization status and table counts
    migrations          - Show current migration status
    seed                - Seed database with demo data
    clear-audit         - Clear all audit logs
    drop                - DROP ALL TABLES (use with extreme caution!)
    help                - Show this help message

Examples:
    python -m pqc_secure.db.cli init
    python -m pqc_secure.db.cli health
    python -m pqc_secure.db.cli status
    python -m pqc_secure.db.cli migrations
    python -m pqc_secure.db.cli seed
    python -m pqc_secure.db.cli clear-audit
    python -m pqc_secure.db.cli drop
    """)


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Error: Command required")
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "init":
            print("Initializing database...")
            init_db()
            print("✓ Database initialized successfully")
            
        elif command == "health":
            print("Checking database health...")
            if verify_database_health():
                print("✓ Database is healthy")
            else:
                print("✗ Database health check failed")
                sys.exit(1)
        
        elif command == "status":
            print("Checking database status...")
            if is_database_initialized():
                print("✓ Database is initialized")
                counts = get_table_count()
                print("\nTable counts:")
                for table, count in counts.items():
                    print(f"  {table}: {count} records")
            else:
                print("✗ Database is not initialized")
                print("Run 'python -m pqc_secure.db.cli init' to initialize")
        
        elif command == "migrations":
            print("Checking migration status...")
            status = get_migration_status()
            if status["status"] == "success":
                print("✓ Migration status:")
                print(f"  Current revision: {status['current_revision']}")
            else:
                print("✗ Failed to get migration status:")
                print(f"  {status['message']}")
        
        elif command == "seed":
            print("Seeding demo data...")
            if not is_database_initialized():
                print("Error: Database not initialized. Run 'init' first.")
                sys.exit(1)
            seed_demo_data()
            print("✓ Demo data seeded successfully")
        
        elif command == "clear-audit":
            print("Clearing audit logs...")
            count = clear_audit_logs()
            print(f"✓ Cleared {count} audit log entries")
        
        elif command == "drop":
            print("WARNING: This will delete ALL data from the database!")
            confirm = input("Are you sure? Type 'yes' to confirm: ")
            if confirm.lower() == "yes":
                drop_all_tables()
                print("✓ All tables dropped successfully")
            else:
                print("Operation cancelled")
        
        elif command == "help":
            print_usage()
        
        else:
            print(f"Error: Unknown command '{command}'")
            print_usage()
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
