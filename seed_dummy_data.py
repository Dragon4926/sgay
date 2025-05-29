import os
import sys
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Add the parent directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import db, User, Project, Beneficiary, ConstructionUpdate, Notification, app

# Sikkim district data
DISTRICTS = ["East Sikkim", "West Sikkim", "North Sikkim", "South Sikkim"]

# Villages by district
VILLAGES = {
    "East Sikkim": ["Gangtok", "Pakyong", "Rangpo", "Rhenock", "Rongli", "Singtam"],
    "West Sikkim": ["Gyalshing", "Soreng", "Dentam", "Kaluk", "Pelling", "Yuksom"],
    "North Sikkim": ["Mangan", "Chungthang", "Dzongu", "Lachen", "Lachung"],
    "South Sikkim": ["Namchi", "Jorethang", "Ravangla", "Temi", "Yangang"]
}

# Realistic Sikkim names
FIRST_NAMES = [
    "Tashi", "Pema", "Karma", "Dawa", "Sonam", "Yangchen", "Tenzing", "Dorjee", "Phurba", 
    "Rinchen", "Lhakpa", "Mingma", "Pasang", "Pemba", "Nima", "Tsering", "Chewang", "Lakpa", 
    "Jigme", "Wangchuk", "Namgyal", "Gyatso", "Sangay", "Kinley", "Dechen", "Choden"
]

LAST_NAMES = [
    "Bhutia", "Lepcha", "Tamang", "Sherpa", "Gurung", "Rai", "Limboo", "Pradhan", "Chettri", 
    "Subba", "Thapa", "Sharma", "Dorji", "Wangdi", "Lama", "Tshering", "Namgyal", "Gyalpo", 
    "Yonzon", "Kazi", "Khaling", "Barfungpa", "Densapa", "Kharga"
]

# Construction stages in order
CONSTRUCTION_STAGES = [
    "Site Preparation", 
    "Foundation", 
    "Plinth Level", 
    "Wall Construction", 
    "Lintel Level", 
    "Roof Level", 
    "Roofing", 
    "Doors and Windows", 
    "Plastering", 
    "Flooring", 
    "Electrical and Plumbing", 
    "Painting", 
    "Finishing", 
    "Completed"
]

# Contractors
CONTRACTORS = [
    "Sikkim Construction Ltd.",
    "Himalayan Builders",
    "East Sikkim Development Corp.",
    "West Sikkim Contractors",
    "North Sikkim Infrastructure Pvt. Ltd.",
    "South Sikkim Construction Company",
    "Mountain Peak Developers",
    "Kanchenjunga Construction",
    "Sikkim State PWD"
]

# Inspectors
INSPECTORS = [
    "Tenzin Norbu", 
    "Dorji Sherpa", 
    "Pemba Tamang", 
    "Mingma Lama", 
    "Karma Bhutia", 
    "Sonam Lepcha", 
    "Pema Wangdi", 
    "Tashi Namgyal"
]

# House types
HOUSE_TYPES = [
    "Single-story house with 2 bedrooms, kitchen, and bathroom",
    "Two-story house with 3 bedrooms, kitchen, and bathroom",
    "Single-story house with 1 bedroom, kitchen, and bathroom",
    "Two-story house with 2 bedrooms, kitchen, bathroom, and small shop",
    "Single-story house with 2 bedrooms, kitchen, bathroom, and verandah",
    "Traditional Sikkim style house with 2 rooms and kitchen"
]

# Image URLs for houses
HOUSE_IMAGES = [
    "https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=500&q=80",
    "https://images.unsplash.com/photo-1598228723793-52759bba239c?auto=format&fit=crop&w=500&q=80",
    "https://images.unsplash.com/photo-1582268611958-ebfd161ef9cf?auto=format&fit=crop&w=500&q=80",
    "https://images.unsplash.com/photo-1576941089067-2de3c901e126?auto=format&fit=crop&w=500&q=80",
    "https://images.unsplash.com/photo-1605146769289-440113cc3d00?auto=format&fit=crop&w=500&q=80",
    "https://images.unsplash.com/photo-1575517111839-3a3843ee7f5d?auto=format&fit=crop&w=500&q=80",
    "https://images.unsplash.com/photo-1572120360610-d971b9d7cae2?auto=format&fit=crop&w=500&q=80",
    "https://images.unsplash.com/photo-1598461861431-a5a24f254353?auto=format&fit=crop&w=500&q=80",
    "https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=500&q=80"
]

# Person images
PERSON_IMAGES = [
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=300&q=80",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80"
]

# Construction update images
CONSTRUCTION_IMAGES = {
    "Site Preparation": "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?auto=format&fit=crop&w=500&q=80",
    "Foundation": "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?auto=format&fit=crop&w=500&q=80",
    "Wall Construction": "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?auto=format&fit=crop&w=500&q=80",
    "Roofing": "https://images.unsplash.com/photo-1574236170880-75fa74701b9b?auto=format&fit=crop&w=500&q=80",
    "Completed": "https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=500&q=80"
}

# Occupations
OCCUPATIONS = ["Farmer", "Daily Wage Laborer", "Self-employed", "Government Employee", "Private Sector Employee", "Teacher", "Shop Owner", "Driver"]

# Social categories
SOCIAL_CATEGORIES = ["General", "SC", "ST", "OBC", "Minority"]

# PMAY Components
PMAY_COMPONENTS = ["BLC", "CLSS", "AHP", "ISSR"]

# Bank names
BANK_NAMES = [
    "State Bank of India",
    "Punjab National Bank",
    "Bank of Baroda",
    "Canara Bank",
    "Union Bank of India",
    "HDFC Bank",
    "ICICI Bank",
    "Axis Bank",
    "Sikkim State Cooperative Bank"
]

# Land ownership status
LAND_OWNERSHIP = ["Own Land", "Family Owned", "No Land"]

# Generate a random Sikkim name
def generate_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

# Generate a random phone number
def generate_phone():
    return f"9{random.randint(1, 9)}{random.randint(10000000, 99999999)}"

# Generate a random Aadhar-like number (not real format)
def generate_aadhar():
    return f"XXXX-XXXX-{random.randint(1000, 9999)}"

# Generate a random email
def generate_email(name):
    domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
    name_parts = name.lower().split()
    username = f"{name_parts[0]}.{name_parts[1]}{random.randint(1, 99)}"
    return f"{username}@{random.choice(domains)}"

# Generate random coordinates within Sikkim
def generate_coordinates(district):
    # Approximate coordinates for districts in Sikkim
    district_coords = {
        "East Sikkim": (27.3389, 88.6065),  # Gangtok area
        "West Sikkim": (27.2833, 88.2667),  # Gyalshing area
        "North Sikkim": (27.5083, 88.5333),  # Mangan area
        "South Sikkim": (27.1667, 88.3667)   # Namchi area
    }
    
    base_lat, base_lng = district_coords[district]
    # Add some randomness within a small radius
    lat = base_lat + (random.random() - 0.5) * 0.1
    lng = base_lng + (random.random() - 0.5) * 0.1
    
    return lat, lng

def seed_db():
    with app.app_context():
        db.create_all()
        
        # Seed Users
        if User.query.count() == 0:
            print("Seeding users...")
            
            # Admin user
            admin = User(
                username='admin', 
                password_hash=generate_password_hash('admin123'), 
                role='admin',
                full_name='Admin User',
                email='admin@pmaysikkim.gov.in',
                phone='9876543210',
                preferred_scheme='pmay',
                created_at=datetime.utcnow() - timedelta(days=120)
            )
            db.session.add(admin)
            
            # Regular users
            regular_users = []
            for i in range(15):
                name = generate_name()
                user = User(
                    username=name.split()[0].lower() + str(i+1),
                    password_hash=generate_password_hash(f"password{i+1}"),
                    role='user',
                    full_name=name,
                    email=generate_email(name),
                    phone=generate_phone(),
                    preferred_scheme=random.choice(['pmay', 'sgay']),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(30, 100))
                )
                regular_users.append(user)
            
            db.session.bulk_save_objects(regular_users)
            db.session.commit()
            print(f"Seeded {len(regular_users) + 1} users.")
        
        # Get all users for reference
        users = User.query.filter(User.role == 'user').all()
        
        # Seed Beneficiaries
        if Beneficiary.query.count() == 0:
            print("Seeding beneficiaries...")
            
            beneficiaries = []
            for i, user in enumerate(users):
                district = random.choice(DISTRICTS)
                village = random.choice(VILLAGES[district])
                
                # Determine status and progress
                status_options = ["Completed", "In Progress", "Pending"]
                status_weights = [0.3, 0.5, 0.2]  # 30% completed, 50% in progress, 20% pending
                status = random.choices(status_options, weights=status_weights, k=1)[0]
                
                if status == "Completed":
                    progress = 100
                    application_date = datetime.utcnow() - timedelta(days=random.randint(90, 180))
                    approval_date = application_date + timedelta(days=random.randint(10, 30))
                elif status == "In Progress":
                    progress = random.randint(25, 90)
                    application_date = datetime.utcnow() - timedelta(days=random.randint(45, 120))
                    approval_date = application_date + timedelta(days=random.randint(10, 30))
                else:  # Pending
                    progress = 0
                    application_date = datetime.utcnow() - timedelta(days=random.randint(1, 30))
                    approval_date = None
                
                # Determine scheme
                scheme = user.preferred_scheme if user.preferred_scheme else random.choice(['pmay', 'sgay'])
                id_prefix = 'PMAY' if scheme == 'pmay' else 'SGAY'
                
                beneficiary = Beneficiary(
                    beneficiary_id=f"{id_prefix}-{1001 + i}",
                    name=user.full_name,
                    district=district,
                    village=village,
                    status=status,
                    progress=progress,
                    contactNumber=user.phone,
                    address=f"Near {random.choice(['Market', 'School', 'Temple', 'Hospital', 'Bus Stand'])}, {village}, {district}",
                    applicationDate=application_date.strftime('%Y-%m-%d'),
                    approvalDate=approval_date.strftime('%Y-%m-%d') if approval_date else None,
                    annual_income=random.randint(150000, 300000),
                    family_members=random.randint(2, 8),
                    aadhar_number=generate_aadhar(),
                    photo_url=random.choice(PERSON_IMAGES),
                    occupation=random.choice(OCCUPATIONS),
                    housing_status=random.choice(["Homeless", "Kutcha House", "Rented"]),
                    user_id=user.id,
                    scheme=scheme,
                    gender=random.choice(['Male', 'Female', 'Other']),
                    category=random.choice(SOCIAL_CATEGORIES),
                    bank_name=random.choice(BANK_NAMES),
                    account_number=f"{random.randint(10000000, 99999999)}",
                    ifsc_code=f"SBIN0{random.randint(10000, 99999)}",
                    land_ownership=random.choice(LAND_OWNERSHIP),
                    property_area=random.randint(800, 2000),
                    pmay_component=random.choice(PMAY_COMPONENTS) if scheme == 'pmay' else None
                )
                beneficiaries.append(beneficiary)
            
            db.session.bulk_save_objects(beneficiaries)
            db.session.commit()
            print(f"Seeded {len(beneficiaries)} beneficiaries.")
        
        # Get all beneficiaries for reference
        beneficiaries = Beneficiary.query.all()
        
        # Seed Projects
        if Project.query.count() == 0:
            print("Seeding projects...")
            
            projects = []
            for i, beneficiary in enumerate(beneficiaries):
                # Skip some beneficiaries (those with pending status)
                if beneficiary.status == "Pending":
                    continue
                
                # Generate coordinates based on district
                lat, lng = generate_coordinates(beneficiary.district)
                
                # Determine project details based on beneficiary status
                if beneficiary.status == "Completed":
                    start_date = datetime.strptime(beneficiary.approvalDate, '%Y-%m-%d') if beneficiary.approvalDate else datetime.utcnow() - timedelta(days=90)
                    end_date = start_date + timedelta(days=random.randint(60, 120))
                    end_date_str = end_date.strftime('%Y-%m-%d')
                else:  # In Progress
                    start_date = datetime.strptime(beneficiary.approvalDate, '%Y-%m-%d') if beneficiary.approvalDate else datetime.utcnow() - timedelta(days=45)
                    end_date_str = None
                
                # Set allocation amount based on scheme
                allocation = 150000 if beneficiary.scheme == 'sgay' else 200000
                
                project = Project(
                    project_id=f"{beneficiary.scheme.upper()}-P{1001 + i}",
                    beneficiaryName=beneficiary.name,
                    location=beneficiary.village,
                    district=beneficiary.district,
                    status=beneficiary.status,
                    allocation=allocation,
                    completionPercentage=beneficiary.progress,
                    startDate=start_date.strftime('%Y-%m-%d'),
                    imageUrl=random.choice(HOUSE_IMAGES),
                    latitude=lat,
                    longitude=lng,
                    description=f"{beneficiary.scheme.upper()} Housing Project: {random.choice(HOUSE_TYPES)}",
                    end_date=end_date_str,
                    contractor=random.choice(CONTRACTORS),
                    beneficiary_id=beneficiary.beneficiary_id
                )
                projects.append(project)
            
            db.session.bulk_save_objects(projects)
            db.session.commit()
            print(f"Seeded {len(projects)} projects.")
        
        # Get all projects for reference
        projects = Project.query.all()
        
        # Seed Construction Updates
        if ConstructionUpdate.query.count() == 0:
            print("Seeding construction updates...")
            
            updates = []
            for project in projects:
                beneficiary = Beneficiary.query.filter_by(beneficiary_id=project.beneficiary_id).first()
                if not beneficiary:
                    continue
                
                # Determine how many updates to create based on progress
                if project.status == "Completed":
                    num_updates = len(CONSTRUCTION_STAGES)
                    stages = CONSTRUCTION_STAGES
                elif project.status == "In Progress":
                    progress_index = int((project.completionPercentage / 100) * len(CONSTRUCTION_STAGES))
                    num_updates = max(1, progress_index)
                    stages = CONSTRUCTION_STAGES[:num_updates]
                else:
                    continue  # Skip pending projects
                
                # Create updates for each stage
                start_date = datetime.strptime(project.startDate, '%Y-%m-%d')
                inspector = random.choice(INSPECTORS)
                
                for i, stage in enumerate(stages):
                    # Calculate date for this update
                    if project.end_date and i == len(stages) - 1:
                        update_date = datetime.strptime(project.end_date, '%Y-%m-%d')
                    else:
                        days_since_start = int((i / len(CONSTRUCTION_STAGES)) * 90)  # Assume 90 days for full construction
                        update_date = start_date + timedelta(days=days_since_start)
                    
                    # Calculate completion percentage for this stage
                    completion_percentage = int(((i + 1) / len(CONSTRUCTION_STAGES)) * 100)
                    
                    # Get appropriate image for this stage
                    if stage in CONSTRUCTION_IMAGES:
                        image_url = CONSTRUCTION_IMAGES[stage]
                    else:
                        # Find the closest stage that has an image
                        for known_stage in CONSTRUCTION_IMAGES.keys():
                            if known_stage in stage or stage in known_stage:
                                image_url = CONSTRUCTION_IMAGES[known_stage]
                                break
                        else:
                            image_url = random.choice(list(CONSTRUCTION_IMAGES.values()))
                    
                    update = ConstructionUpdate(
                        beneficiaryId=beneficiary.beneficiary_id,
                        district=beneficiary.district,
                        location=beneficiary.village,
                        constructionStage=stage,
                        completionPercentage=completion_percentage,
                        notes=f"{stage} completed successfully." if i < len(stages) - 1 else "Construction completed and ready for handover.",
                        photos=image_url,
                        timestamp=int(update_date.timestamp()),
                        update_date=update_date,
                        inspector=inspector,
                        project_id=project.project_id
                    )
                    updates.append(update)
            
            db.session.bulk_save_objects(updates)
            db.session.commit()
            print(f"Seeded {len(updates)} construction updates.")
        
        # Seed Notifications
        if Notification.query.count() == 0:
            print("Seeding notifications...")
            
            notifications = []
            for beneficiary in beneficiaries:
                if not beneficiary.user_id:
                    continue
                
                # Application submitted notification
                app_date = datetime.strptime(beneficiary.applicationDate, '%Y-%m-%d') if beneficiary.applicationDate else datetime.utcnow() - timedelta(days=random.randint(30, 90))
                notifications.append(Notification(
                    user_id=beneficiary.user_id,
                    title="Application Submitted",
                    message=f"Your housing application (ID: {beneficiary.beneficiary_id}) has been submitted successfully. We will review it shortly.",
                    is_read=True,
                    created_at=app_date
                ))
                
                # Application approved notification (if applicable)
                if beneficiary.approvalDate:
                    approval_date = datetime.strptime(beneficiary.approvalDate, '%Y-%m-%d')
                    notifications.append(Notification(
                        user_id=beneficiary.user_id,
                        title="Application Approved",
                        message=f"Your housing application (ID: {beneficiary.beneficiary_id}) has been approved. Construction will begin soon.",
                        is_read=random.choice([True, False]),
                        created_at=approval_date
                    ))
                
                # Construction updates (if applicable)
                project = Project.query.filter_by(beneficiary_id=beneficiary.beneficiary_id).first()
                if project and project.status != "Pending":
                    # Construction started
                    start_date = datetime.strptime(project.startDate, '%Y-%m-%d')
                    notifications.append(Notification(
                        user_id=beneficiary.user_id,
                        title="Construction Started",
                        message=f"Construction of your house has started. You can track your project's progress on the Progress page.",
                        is_read=random.choice([True, False]),
                        created_at=start_date
                    ))
                    
                    # Progress update (for in-progress or completed)
                    if project.completionPercentage >= 50:
                        progress_date = start_date + timedelta(days=int(project.completionPercentage * 0.3))
                        notifications.append(Notification(
                            user_id=beneficiary.user_id,
                            title="Construction Update",
                            message=f"Your house construction is {project.completionPercentage}% complete.",
                            is_read=random.choice([True, False]),
                            created_at=progress_date
                        ))
                    
                    # Completion notification (if completed)
                    if project.status == "Completed":
                        completion_date = datetime.strptime(project.end_date, '%Y-%m-%d') if project.end_date else datetime.utcnow() - timedelta(days=random.randint(1, 30))
                        notifications.append(Notification(
                            user_id=beneficiary.user_id,
                            title="Construction Completed",
                            message="Your house construction is now complete. Please visit the office for handover.",
                            is_read=False,
                            created_at=completion_date
                        ))
            
            db.session.bulk_save_objects(notifications)
            db.session.commit()
            print(f"Seeded {len(notifications)} notifications.")
        
        print("Dummy data seeding complete.")

if __name__ == "__main__":
    seed_db()
