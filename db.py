from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask

# Create the Flask application
app = Flask(__name__)

# Configure database URI
# ** TEMPORARY URL**
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quickfi.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy with the Flask app
db = SQLAlchemy()
db.init_app(app)

class Account(db.Model):
    """Account model
    Has a one-to-many relationshp with Equipment table"""
    __tablename__ = "Account"

    ID = db.Column(db.String, primary_key=True, nullable = False)
    Name = db.Column(db.String)
    Street = db.Column(db.String)
    City = db.Column(db.String)
    State = db.Column(db.String)
    ZIP = db.Column(db.Integer)
    LiabilityEmail = db.Column(db.String)
    PropertyEmail = db.Column(db.String)
    InsuranceFolderID = db.Column(db.Integer)
    LiabilityExpirationDate = db.Column(db.String)
    PropertyExpirationDate = db.Column(db.Date)
    InsuranceCoordinator = db.Column(db.String)

    #one to many
    equipment = db.relationship("Equipment", back_populates = "account")

class Vendor(db.Model):
    """Vendor model"""
    __tablename__ = "Vendor"
    ID = db.Column(db.String, primary_key=True, nullable = False)
    Name = db.Column(db.String)
    Street = db.Column(db.String)
    City = db.Column(db.String)
    State = db.Column(db.String)
    ZIP = db.Column(db.Integer)
    Website = db.Column(db.String)
    DnbHeadquartersState = db.Column(db.String)

    #one to many
    equipment = db.relationship("Equipment", back_populates = "vendor")

class Lender(db.Model):
    """Lender model"""
    __tablename__ = "Lender"
    ID = db.Column(db.String, primary_key=True, nullable = False)
    Name = db.Column(db.String)
    CertificateHolderAddress = db.Column(db.String)

    #one to many
    equipment = db.relationship("Equipment", back_populates = "lender")


class Equipment(db.Model):
    """Equipment Model
    Many-to-one with Vendor Table
    Many-to-one with Lender Table
    Many-to-one with Account Table"""
    __tablename__ = "Equipment"

    ID = db.Column(db.Integer, primary_key=True, autoincrement = True)
    AccountID = db.Column(db.Integer, db.ForeignKey("Account.ID"))
    Year = db.Column(db.Integer)
    Make = db.Column(db.String)
    Model = db.Column(db.String)
    SerialNumber = db.Column(db.String)
    CostPerUnit = db.Column(db.String)
    VendorID = db.Column(db.String, db.ForeignKey("Vendor.ID"))
    LenderID = db.Column(db.String, db.ForeignKey("Lender.ID"))

    #relationships for easier access
    account = db.relationship("Account", back_populates = "equipment")
    lender = db.relationship("Lender", back_populates = "equipment")
    vendor = db.relationship("Vendor", back_populates = "equipment")

# Move table creation into a function that can be called with app context
def init_db():
    with app.app_context():
        db.create_all()

# Create tables when this module is run directly
if __name__ == "__main__":
    init_db()

class DatabaseDriver:
    """
    Database driver using Flask-SQLAlchemy
    Handles reading and writing information with database
    """
    def __init__(self):
        """
        Creates session
        """
        self.session = db.session

    
    def get_account_by_id(self, account_id):
        """
        Returns information about an account given an account ID.
        """
        account = self.session.query(Account).filter(Account.ID == account_id).first()
        if account:
            LenderName = None
            if account.equipment: 
                for equipment in account.equipment: 
                    if equipment.lender: 
                        LenderName = equipment.lender.Name 
                        break
            return {
                "Account.Name": account.Name,
                "Account.Address": f"{account.Street}, {account.City}, {account.State}, {account.ZIP}",
                "LiabilityEmail": account.LiabilityEmail,
                "PropertyEmail": account.PropertyEmail,
                "Lender.Name": LenderName, 
                "InsuranceFolderID": account.InsuranceFolderID,
                "LiabilityExpirationDate": account.LiabilityExpirationDate,
                "PropertyExpirationDate": account.PropertyExpirationDate,
                "InsuranceCoordinator": account.InsuranceCoordinator
            }
        return None
    

    def get_equipment_by_account_id(self, account_id):
        """
        Returns information about the equipment listed under a given account ID.
        """
        equipment_records = self.session.query(Equipment).filter(Equipment.AccountID == account_id).all()
        return [
            {
                "Year": equipment.Year,
                "Make": equipment.Make,
                "Model": equipment.Model,
                "Serial": equipment.SerialNumber,
                "CostPerUnit": equipment.CostPerUnit
            }
            for equipment in equipment_records
        ]
    
    def due_diligence_check(self, account_id, vendor_id):
        """
        Returns the data needed to run due diligence checks
        """
        account = self.session.query(Account).filter(Account.ID.equals(account_id)).first()
        vendor = self.session.query(Vendor).filter(Vendor.ID.equals(vendor_id)).first()
        if account:
            return {
                "Account.Name": account.Name,
                "Account.Address": f"{account.Street}, {account.City}, {account.State}, {account.ZIP}",
                "Vendor.Name": vendor.Name,
                "Vendor.Address": f"{vendor.Street}, {vendor.City}, {vendor.State}, {vendor.ZIP}",
                "Vendor.Website": vendor.Website       
        }
