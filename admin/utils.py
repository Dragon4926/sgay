from datetime import datetime, timedelta, date
from flask import session, url_for
import json
from app import db
from models import User, Project, Beneficiary, Notification
from sqlalchemy import func, cast, Date as SQLDate # Added for date operations
from collections import defaultdict, OrderedDict # Added for chart data preparation

class AdminUtils:
    @staticmethod
    def get_beneficiary_registration_trend_chart_data():
        """Prepares data for beneficiary registration trend chart (e.g., monthly)."""
        today = date.today()
        labels = []
        data = []
        # Generate labels for the last 6 months
        for i in range(5, -1, -1):
            month_year = today.replace(day=1) - timedelta(days=i*30) # Approximate months
            labels.append(month_year.strftime("%b %Y"))

        # Query beneficiary counts grouped by month of creation
        # Assuming Beneficiary model has a `created_at` (DateTime) or `applicationDate` (String YYYY-MM-DD) field
        # For this example, let's assume `created_at` exists and is a DateTime field.
        # If using `applicationDate` (string), conversion/casting will be needed.
        
        six_months_ago = today.replace(day=1) - timedelta(days=6*30)
        
        # Check if Beneficiary has created_at, otherwise use a placeholder for applicationDate logic
        if hasattr(Beneficiary, 'created_at'):
            # Assuming Beneficiary.created_at is a DateTime field
            registrations = (db.session.query(
                func.strftime("%Y-%m", Beneficiary.created_at).label('month_year'),
                func.count(Beneficiary.id).label('count')
            ).filter(Beneficiary.created_at >= six_months_ago)
            .group_by('month_year')
            .order_by('month_year')
            .all())
            monthly_counts = {r.month_year: r.count for r in registrations}
        elif hasattr(Beneficiary, 'applicationDate'): # Assuming applicationDate is YYYY-MM-DD string
            # This is more complex due to string date. A proper DateTime field is better.
            # In a real scenario, you'd parse applicationDate or cast it in the query.
            registrations = (db.session.query(
                func.substr(Beneficiary.applicationDate, 1, 7).label('month_year'), # Extracts YYYY-MM
                func.count(Beneficiary.id).label('count')
            ).filter(cast(Beneficiary.applicationDate, SQLDate) >= six_months_ago)
            .group_by(func.substr(Beneficiary.applicationDate, 1, 7))
            .order_by(func.substr(Beneficiary.applicationDate, 1, 7))
            .all())
            monthly_counts = {r.month_year: r.count for r in registrations}
        else:
            # Fallback to mock data if no suitable date field is found
            monthly_counts = {}

        # Populate data ensuring all months in labels have a value
        for month_label_dt_approx in [today.replace(day=1) - timedelta(days=i*30) for i in range(5, -1, -1)]:
            month_year_str = month_label_dt_approx.strftime("%Y-%m")
            data.append(monthly_counts.get(month_year_str, 0))
        
        # If data is empty (e.g. no recent beneficiaries), fill with zeros or some default
        if not any(data):
            data = [5, 10, 8, 15, 12, 20] # Example mock data if no real data
            if not labels: # If labels also failed
                 labels = [ (date.today() - timedelta(days=i*30)).strftime("%b %Y") for i in range(5,-1,-1)]


        return {
            'labels': labels,
            'datasets': [{
                'label': 'New Beneficiaries',
                'data': data,
                'borderColor': '#1abc9c',
                'backgroundColor': 'rgba(26, 188, 156, 0.1)',
                'fill': True,
                'tension': 0.3
            }]
        }

    @staticmethod
    def get_project_funding_distribution_chart_data():
        """Prepares data for project funding distribution (pie chart) - MOCK DATA."""
        # This is mock data. In a real application, query Project model for funding sources/categories.
        return {
            'labels': ['Government Grants', 'Private Donations', 'Corporate Sponsorship', 'International Aid'],
            'datasets': [{
                'label': 'Funding Distribution',
                'data': [1200000, 750000, 500000, 300000],
                'backgroundColor': [
                    '#3498db', # Blue
                    '#2ecc71', # Green
                    '#f1c40f', # Yellow
                    '#e74c3c'  # Red
                ],
                'hoverOffset': 4
            }]
        }

    @staticmethod
    def get_dashboard_stats():
        """
        Get statistics for the admin dashboard, including chart data.
        """
        common_stats = {
            'total_beneficiaries': Beneficiary.query.count(),
            'total_projects': Project.query.count(),
            'total_districts': db.session.query(Project.district).distinct().count()
        }
        
        dashboard_data = {
            **common_stats,
            'active_users': User.query.filter(User.last_login > datetime.utcnow() - timedelta(days=30)).count(),
            'system_notifications': Notification.query.filter_by(is_read=False).count(),
            'pending_approvals': Project.query.filter(Project.status.like('Pending%')).count(),
            'reported_issues': 0, # Placeholder
            'beneficiary_registration_trend': AdminUtils.get_beneficiary_registration_trend_chart_data(),
            'project_funding_distribution': AdminUtils.get_project_funding_distribution_chart_data()
        }
        return dashboard_data

    @staticmethod
    def get_recent_activities(limit=5):
        """
        Get recent activities based on the admin's role.
        This should query an Activity/Log model in a real application.
        For now, returning fewer mock activities or querying notifications.
        """
        query = Notification.query.order_by(Notification.created_at.desc())

        recent_notifications = query.limit(limit).all()
        activities = []
        for notif in recent_notifications:
            activities.append({
                'id': notif.id,
                'type': 'notification',
                'description': notif.message,
                'timestamp': notif.created_at,
                'priority': 'medium'
            })
        
        if not activities:
            now = datetime.now()
            common_activities = [
                {
                    'id': 1,
                    'type': 'system_update',
                    'description': 'System maintenance scheduled for Sunday, 02:00 AM',
                    'timestamp': now - timedelta(hours=2),
                    'priority': 'high'
                }
            ]
            activities = common_activities

        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:limit]

    @staticmethod
    def get_pending_tasks():
        """
        Get pending tasks for the admin.
        These should be derived from database queries.
        """
        tasks = []
        now = datetime.now()

        # Admin specific tasks
        pending_admin_approvals = Project.query.filter(Project.status.like('Pending%')).count()
        if pending_admin_approvals > 0:
                tasks.append({
                'id': 'admin_approval',
                'title': 'Pending Approvals',
                'description': f'There are {pending_admin_approvals} items awaiting administrative approval.',
                'due_date': (now + timedelta(days=1)).strftime('%Y-%m-%d'),
                'priority': 'high',
                'link': url_for('admin.admin_dashboard') # Make sure admin_dashboard route exists and is correct
            })

        return tasks

    @staticmethod
    def get_projects_summary(role=None):
        """
        Get a summary of projects.
        This should query the Project model.
        """
        try:
            total_projects = Project.query.count()
            completed_projects = Project.query.filter_by(status='Completed').count()
            in_progress_projects = Project.query.filter_by(status='In Progress').count()
            pending_projects = Project.query.filter(Project.status.like('Pending%')).count()

            # Get district data for charts
            districts_query = db.session.query(
                Project.district, 
                db.func.count(Project.id),
                db.func.avg(Project.completionPercentage)
            ).group_by(Project.district).all()
            
            districts = []
            for district, count, completion_avg in districts_query:
                districts.append({
                    'name': district,
                    'count': count,
                    'completion_rate': round(completion_avg if completion_avg is not None else 0, 2)
                })

            # Add chart data for historical view (placeholder data)
            chart_data = {
                'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                'datasets': [
                    {
                        'label': 'Completed',
                        'data': [10, 15, 22, 35, 41, 59]
                    },
                    {
                        'label': 'Started',
                        'data': [30, 45, 55, 65, 80, 95]
                    }
                ]
            }

            summary = {
                'total': total_projects,
                'completed': completed_projects,
                'in_progress': in_progress_projects,
                'planning': pending_projects,
                'status_distribution': [
                    {'status': 'Completed', 'count': completed_projects, 'percentage': (completed_projects / total_projects * 100) if total_projects else 0},
                    {'status': 'In Progress', 'count': in_progress_projects, 'percentage': (in_progress_projects / total_projects * 100) if total_projects else 0},
                    {'status': 'Pending', 'count': pending_projects, 'percentage': (pending_projects / total_projects * 100) if total_projects else 0},
                ],
                'funding_overview': {
                    'total_allocated': f"₹{db.session.query(db.func.sum(Project.allocation)).scalar() or 0 / 10000000:.1f} Cr",
                    'total_spent': f"₹{db.session.query(db.func.sum(Project.allocation)).filter(Project.status != 'Pending Sanction').scalar() or 0 / 10000000:.1f} Cr"
                },
                'districts': districts,
                'chart_data': chart_data,
                # Pre-process district data for template
                'districts_data': {
                    'names': [d['name'] for d in districts],
                    'counts': [d['count'] for d in districts],
                    'completion_rates': [d['completion_rate'] for d in districts]
                }
            }
            return summary
        except Exception as e:
            # Log the error
            print(f"Error in get_projects_summary: {str(e)}")
            # Return default values
            return {
                'total': 0,
                'completed': 0,
                'in_progress': 0,
                'planning': 0,
                'status_distribution': [
                    {'status': 'Completed', 'count': 0, 'percentage': 0},
                    {'status': 'In Progress', 'count': 0, 'percentage': 0},
                    {'status': 'Pending', 'count': 0, 'percentage': 0},
                ],
                'funding_overview': {
                    'total_allocated': '₹0.0 Cr',
                    'total_spent': '₹0.0 Cr'
                },
                'districts': [],
                'chart_data': {
                    'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    'datasets': [
                        {
                            'label': 'Completed',
                            'data': [0, 0, 0, 0, 0, 0]
                        },
                        {
                            'label': 'Started',
                            'data': [0, 0, 0, 0, 0, 0]
                        }
                    ]
                },
                'districts_data': {
                    'names': [],
                    'counts': [],
                    'completion_rates': []
                }
            }

    @staticmethod
    def get_beneficiaries_summary(role=None):
        """
        Get a summary of beneficiaries.
        This should query the Beneficiary model.
        """
        try:
            total_beneficiaries = Beneficiary.query.count()
            verified_beneficiaries = Beneficiary.query.filter_by(status='Verified').count()
            pending_verification = Beneficiary.query.filter_by(status='Pending Verification').count()

            beneficiaries_by_district = db.session.query(Beneficiary.district, func.count(Beneficiary.id)).group_by(Beneficiary.district).all()
            district_distribution = [{'district': d, 'count': c} for d, c in beneficiaries_by_district]

            # Monthly registration trend data moved to its own function get_beneficiary_registration_trend_chart_data

            summary = {
                'total': total_beneficiaries,
                'verification_status': [
                    {'status': 'Verified', 'count': verified_beneficiaries, 'percentage': (verified_beneficiaries / total_beneficiaries * 100) if total_beneficiaries else 0},
                    {'status': 'Pending Verification', 'count': pending_verification, 'percentage': (pending_verification / total_beneficiaries * 100) if total_beneficiaries else 0},
                ],
                'district_distribution': district_distribution,
                'demographics': {} # Placeholder for more detailed demographics
            }
            return summary
        except Exception as e:
            # Log the error
            print(f"Error in get_beneficiaries_summary: {str(e)}")
            # Return default values
            return {
                'total': 0,
                'verification_status': [
                    {'status': 'Verified', 'count': 0, 'percentage': 0},
                    {'status': 'Pending Verification', 'count': 0, 'percentage': 0},
                ],
                'district_distribution': [],
                'demographics': {}
            }

    @staticmethod
    def get_financial_summary(role=None):
        """
        Get a financial summary. 
        (Simplified for admin-only view)
        """
        # For a general admin, we might show overall budget status or key financial indicators.
        # For now, returning a simple structure. This can be expanded based on admin needs.
        
        try:
            total_allocation = db.session.query(db.func.sum(Project.allocation)).scalar() or 0
            disbursed_allocation = db.session.query(db.func.sum(Project.allocation)).filter(Project.status.in_(['Funds Disbursed', 'Completed'])).scalar() or 0 # Assuming 'Completed' projects also had funds disbursed

            return {
                'total_budget_allocated': f'₹ {total_allocation / 10000000:.2f} Cr',
                'total_funds_disbursed': f'₹ {disbursed_allocation / 10000000:.2f} Cr',
                'fund_utilization_percentage': round((disbursed_allocation / total_allocation * 100), 2) if total_allocation else 0,
                # Add more admin-relevant financial stats here if needed
            }
        except Exception as e:
            # Log the error
            print(f"Error in get_financial_summary: {str(e)}")
            # Return default values
            return {
                'total_budget_allocated': '₹ 0.00 Cr',
                'total_funds_disbursed': '₹ 0.00 Cr',
                'fund_utilization_percentage': 0,
            }

    @staticmethod
    def get_verification_tasks(role=None, limit=10):
        """
        Get beneficiary verification tasks, e.g., for Nodal Officers.
        Queries Beneficiary model for those needing verification.
        """
        pending_verification = Beneficiary.query.filter_by(status='Pending Verification') \
                                          .order_by(Beneficiary.applicationDate.asc()) \
                                          .limit(limit).all()
        tasks = []
        for ben in pending_verification:
            priority_val = 'medium'  # Default priority
            if ben.applicationDate:
                try:
                    application_date_obj = datetime.strptime(ben.applicationDate, '%Y-%m-%d')
                    if (datetime.utcnow() - application_date_obj).days > 7:
                        priority_val = 'high'
                except ValueError:
                    # In a real application, you might want to log this warning:
                    # from flask import current_app
                    # current_app.logger.warning(f"Invalid applicationDate format for beneficiary {ben.beneficiary_id}: {ben.applicationDate}")
                    pass  # Keep default priority 'medium' or assign a specific one for parse errors

            tasks.append({
                'id': ben.beneficiary_id,
                'beneficiary_name': ben.name,
                'district': ben.district,
                'application_date': ben.applicationDate,  # Keep original string for display
                'status': ben.status,
                'priority': priority_val,
                'link': url_for('admin.verify_beneficiary_detail', task_id=ben.beneficiary_id)
            })
        return tasks

    @staticmethod
    def get_sanction_requests(role=None, limit=10):
        """
        Get fund sanction requests, e.g., for State Authorities.
        Queries Project model for those pending sanction.
        (Adjusted for general admin view)
        """
        # If admins need to see/manage sanction requests, this is a starting point.
        # Otherwise, this can be an empty list or removed if not applicable to general admin.
        pending_sanction = Project.query.filter_by(status='Pending Sanction') \
                                        .order_by(Project.created_at.asc()) \
                                        .limit(limit).all()
        
        sanction_requests_list = []
        for project in pending_sanction:
            sanction_requests_list.append({
                'id': project.id,
                'batch_id': project.project_id, 
                'district': project.district,
                'beneficiary_count': Beneficiary.query.filter_by(project_id=project.id).count(), # Example calculation
                'total_amount': f"₹ {project.allocation / 100000:.1f} Lakhs",
                'submitted_by': 'Nodal Officer', # In a real app, this would be the actual user who submitted
                'submission_date': project.created_at.strftime('%Y-%m-%d') if project.created_at else 'N/A',
                'status': 'pending_approval',
                'priority': 'medium',
                'link': url_for('admin.sanction_fund_detail', request_id=project.project_id)
            })
        return sanction_requests_list

    # Placeholder for other utility functions that might be needed
    # Example:
    # @staticmethod
    # def get_user_details(user_id):
    #     user = User.query.get(user_id)
    #     if user:
    #         return {'id': user.id, 'username': user.username, 'role': user.role, 'full_name': user.full_name}
    #     return None