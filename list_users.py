"""
Script to list all users in the database and their roles.
This is useful for debugging the authentication system.
"""
from app import app, db
from models import User, Property

def list_users():
    """List all users in the database with their roles and properties."""
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("No users found in the database.")
            return
        
        print(f"Found {len(users)} users:")
        print("-" * 80)
        print(f"{'ID':<5} {'Email':<30} {'Role':<15} {'Property':<20} {'Last Login'}")
        print("-" * 80)
        
        for user in users:
            property_info = "None"
            if user.property_id:
                property = Property.query.get(user.property_id)
                if property:
                    property_info = f"Unit {property.unit_number}"
            
            last_login = user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "Never"
            
            print(f"{user.id:<5} {user.email:<30} {user.role:<15} {property_info:<20} {last_login}")
        
        print("-" * 80)

if __name__ == "__main__":
    list_users()