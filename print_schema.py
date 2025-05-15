"""
Script to print a human-readable schema of the database from SQLAlchemy models.
This helps with understanding the database structure without needing database access.
"""
import os
import inspect
from app import app, db
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.sql.schema import ForeignKey

def print_schema():
    """Print a human-readable schema of all models in the database."""
    with app.app_context():
        # Get all models from imported modules
        models = {}
        
        # Import all models
        import models as models_module
        
        # Find all model classes that inherit from db.Model
        for name, obj in inspect.getmembers(models_module):
            if inspect.isclass(obj) and issubclass(obj, db.Model) and obj != db.Model:
                models[name] = obj
        
        print("\n=== DATABASE SCHEMA ===\n")
        print(f"Found {len(models)} models:\n")
        
        # Print each model's schema
        for model_name, model in sorted(models.items()):
            print(f"### {model_name} ###")
            
            # Get model's table name
            table_name = model.__tablename__ if hasattr(model, '__tablename__') else model.__table__.name
            print(f"Table: {table_name}")
            
            # Get docstring if available
            if model.__doc__:
                print(f"Description: {model.__doc__.strip()}")
            
            # Get column information
            print("\nColumns:")
            inspector = sqlalchemy_inspect(db.engine)
            columns = {}
            
            try:
                # Try to get columns from database
                columns = {col['name']: col for col in inspector.get_columns(table_name)}
            except:
                # If fails, get columns from model
                for name, column in model.__table__.columns.items():
                    columns[name] = {
                        'name': name,
                        'type': str(column.type),
                        'nullable': column.nullable,
                        'default': str(column.default) if column.default else None,
                        'primary_key': column.primary_key,
                    }
            
            # Print columns
            for column_name, column in sorted(columns.items()):
                constraints = []
                if column.get('primary_key'):
                    constraints.append('PRIMARY KEY')
                if not column.get('nullable'):
                    constraints.append('NOT NULL')
                # Check for foreign keys - different handling for reflected columns vs model columns
                if isinstance(column.get('type'), ForeignKey) or 'FOREIGN KEY' in str(column):
                    constraints.append('FOREIGN KEY')
                    
                constraints_str = f" ({', '.join(constraints)})" if constraints else ""
                default_str = f" DEFAULT {column.get('default')}" if column.get('default') else ""
                
                print(f"  - {column.get('name')}: {column.get('type')}{constraints_str}{default_str}")
            
            # Print relationships if available
            if hasattr(model, '__mapper__') and hasattr(model.__mapper__, 'relationships'):
                print("\nRelationships:")
                for name, rel in model.__mapper__.relationships.items():
                    target = rel.target.name if hasattr(rel.target, 'name') else str(rel.target)
                    print(f"  - {name} -> {target}")
            
            print("\n")
        
        print("=== END OF SCHEMA ===")

if __name__ == "__main__":
    print_schema()