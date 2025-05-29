import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_vercel_env():
    """Set up the environment for Vercel deployment"""
    try:
        logger.info("Setting up Vercel environment...")
        
        # Detect if we're on Vercel
        is_vercel = os.environ.get('VERCEL', False)
        if is_vercel:
            logger.info("Detected Vercel environment")
            
            # Set appropriate environment variables
            if 'DATABASE_URL' not in os.environ:
                logger.warning("No DATABASE_URL provided, using SQLite")
                # Point to /tmp for SQLite in serverless environment
                os.environ['DATABASE_URL'] = 'sqlite:////tmp/pmay.db'
            
            # Setup other environment variables if needed
            if 'SECRET_KEY' not in os.environ:
                logger.warning("No SECRET_KEY provided, using default (not secure)")
                os.environ['SECRET_KEY'] = 'vercel-deployment-key'
                
            logger.info("Environment setup completed")
            return True
        else:
            logger.info("Not running on Vercel, skipping environment setup")
            return False
    except Exception as e:
        logger.error(f"Error setting up Vercel environment: {str(e)}")
        return False

if __name__ == "__main__":
    setup_vercel_env()
    logger.info("Vercel setup script completed") 