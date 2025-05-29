from datetime import datetime

class BeneficiaryUtils:
    @staticmethod
    def get_project_status(beneficiary_id):
        """
        Get construction status for a beneficiary's project.
        This is a mock implementation - would fetch from database in real app.
        """
        # Mock data - in a real app, this would query the database
        mock_statuses = {
            "B001": {
                "status": "in_progress",
                "completion_percentage": 45,
                "stage": "Wall construction",
                "estimated_completion": "2023-12-15",
                "last_updated": datetime(2023, 5, 15).strftime("%Y-%m-%d")
            },
            "B002": {
                "status": "approved",
                "completion_percentage": 0,
                "stage": "Approved, waiting for construction start",
                "estimated_completion": "2024-03-30",
                "last_updated": datetime(2023, 5, 2).strftime("%Y-%m-%d")
            },
            "B003": {
                "status": "completed",
                "completion_percentage": 100,
                "stage": "Construction complete",
                "estimated_completion": "2023-04-30",
                "last_updated": datetime(2023, 4, 30).strftime("%Y-%m-%d")
            }
        }
        
        # Return the status for the given beneficiary ID, or a default if not found
        return mock_statuses.get(beneficiary_id, {
            "status": "pending",
            "completion_percentage": 0,
            "stage": "Application under review",
            "estimated_completion": "Not available",
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        })
    
    @staticmethod
    def get_payment_history(beneficiary_id):
        """
        Get payment disbursement history for a beneficiary.
        This is a mock implementation - would fetch from database in real app.
        """
        # Mock data - in a real app, this would query the database
        mock_payments = {
            "B001": [
                {
                    "amount": 50000,
                    "date": "2023-02-15",
                    "stage": "Foundation",
                    "status": "disbursed"
                },
                {
                    "amount": 50000,
                    "date": "2023-04-20",
                    "stage": "Walls",
                    "status": "disbursed"
                },
                {
                    "amount": 50000,
                    "date": "2023-06-30",
                    "stage": "Roof",
                    "status": "pending"
                }
            ],
            "B003": [
                {
                    "amount": 50000,
                    "date": "2023-01-10",
                    "stage": "Foundation",
                    "status": "disbursed"
                },
                {
                    "amount": 50000,
                    "date": "2023-02-20",
                    "stage": "Walls",
                    "status": "disbursed"
                },
                {
                    "amount": 50000,
                    "date": "2023-03-25",
                    "stage": "Roof",
                    "status": "disbursed"
                },
                {
                    "amount": 50000,
                    "date": "2023-04-15",
                    "stage": "Finishing",
                    "status": "disbursed"
                }
            ]
        }
        
        return mock_payments.get(beneficiary_id, [])
    
    @staticmethod
    def get_required_documents(beneficiary_id):
        """
        Get list of required documents and their submission status.
        This is a mock implementation - would fetch from database in real app.
        """
        # Common documents required for all beneficiaries
        documents = [
            {
                "type": "aadhar",
                "name": "Aadhar Card",
                "required": True,
                "submitted": True,
                "verified": True
            },
            {
                "type": "income",
                "name": "Income Certificate",
                "required": True,
                "submitted": True,
                "verified": True
            },
            {
                "type": "land",
                "name": "Land Ownership Documents",
                "required": True,
                "submitted": False,
                "verified": False
            },
            {
                "type": "family",
                "name": "Family Certificate",
                "required": True,
                "submitted": True,
                "verified": True
            },
            {
                "type": "bank",
                "name": "Bank Account Details",
                "required": True,
                "submitted": True,
                "verified": False
            }
        ]
        
        return documents 