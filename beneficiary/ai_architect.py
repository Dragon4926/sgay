import os
import requests
import json
import logging
from flask import current_app
from werkzeug.utils import secure_filename
import uuid
import google.generativeai as genai
from PIL import Image
import base64

logger = logging.getLogger(__name__)

class AIArchitectService:
    """Service to handle AI-generated house designs using Gemini"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            logger.warning("Gemini API key not provided. AI Architect will not function properly.")
        else:
            genai.configure(api_key=self.api_key)
        self.model_name = "gemini-pro-vision"
        self.image_model = "gemini-2.0-flash-preview-image-generation"
    
    def _validate_image(self, image_path):
        """Validate if the image exists and is of correct format"""
        if not os.path.exists(image_path):
            raise ValueError(f"Image not found at path: {image_path}")
        
        valid_extensions = ['.jpg', '.jpeg', '.png']
        file_ext = os.path.splitext(image_path)[1].lower()
        
        if file_ext not in valid_extensions:
            raise ValueError(f"Invalid image format. Supported formats: {', '.join(valid_extensions)}")
        
        return True
    
    def _load_image_for_genai(self, image_path):
        """Load image for Google's Generative AI library"""
        return Image.open(image_path)
    
    def _ensure_directory_exists(self, directory_path):
        """Ensure the directory exists, create if it doesn't"""
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
    
    def generate_designs(self, plot_image_path, beneficiary=None, fund_allocation=None, additional_info=None):
        """
        Generate 4 house designs based on the plot image
        
        Parameters:
        - plot_image_path: Path to the uploaded plot image
        - beneficiary: Beneficiary object containing location and other relevant info
        - fund_allocation: Financial allocation for the house construction
        - additional_info: Any additional requirements or preferences
        
        Returns:
        - A list of design dictionaries with URLs, costs, and descriptions
        """
        try:
            # Validate image
            self._validate_image(plot_image_path)
            
            # Prepare context information
            location_info = ""
            budget_info = ""
            
            if beneficiary:
                location_info = f"Location: {beneficiary.district}, {beneficiary.village}, Sikkim, India."
            
            if fund_allocation:
                max_construction_budget = fund_allocation * 0.7  # 70% of allocated fund
                budget_info = f"Maximum budget for construction: Rs. {max_construction_budget:,.2f} (70% of allocated fund of Rs. {fund_allocation:,.2f})"
            
            # Create directory for house designs if it doesn't exist
            designs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'house_designs')
            self._ensure_directory_exists(designs_dir)
            
            # Make actual API call to Gemini
            image = self._load_image_for_genai(plot_image_path)
            
            # Generate 4 different house styles
            styles = ["Traditional Sikkim", "Modern Mountain", "Eco-friendly", "Minimalist Alpine"]
            designs = []
            
            for i, style in enumerate(styles):
                prompt = f"""
                Generate a realistic house design image for a plot of land shown in the attached image.
                {location_info}
                {budget_info}
                
                Design Style: {style}
                
                Please create a realistic house design that:
                1. Fits well in the plot shown
                2. Is appropriate for Sikkim's climate and geography
                3. Uses sustainable and locally available materials where possible
                4. Optimizes space utilization
                5. Is aesthetically pleasing
                """
                
                # Call Gemini API for image generation
                try:
                    generation_config = {
                        "temperature": 0.7,
                        "top_p": 1,
                        "top_k": 32,
                        "max_output_tokens": 2048,
                        "response_mime_type": "image/jpeg"
                    }
                    
                    model = genai.GenerativeModel(
                        model_name=self.image_model,
                        generation_config=generation_config
                    )
                    
                    response = model.generate_content([prompt, image])
                    
                    # Save the generated image
                    design_filename = f"design_{uuid.uuid4().hex[:8]}_{i+1}.jpg"
                    design_path = os.path.join(designs_dir, design_filename)
                    
                    # Extract and save the image from the response
                    if hasattr(response, 'candidates') and len(response.candidates) > 0 and hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts'):
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'file_data') and hasattr(part.file_data, 'mime_type') and 'image' in part.file_data.mime_type:
                                with open(design_path, 'wb') as f:
                                    f.write(part.file_data.file_bytes)
                    
                    # Generate cost estimates
                    cost_factor = 0.5 + (i * 0.05)  # Each design uses different percentage of budget
                    building_cost = max_construction_budget * cost_factor * 0.7 if fund_allocation else 1000000
                    labor_cost = max_construction_budget * cost_factor * 0.3 if fund_allocation else 400000
                    total_cost = building_cost + labor_cost
                    
                    # Get description for the design using Gemini Pro Vision
                    description_prompt = f"""
                    Provide a short, detailed description for this {style} house design.
                    Focus on its suitability for Sikkim's climate, the materials used, 
                    space utilization, and sustainability features.
                    Keep it under 200 characters.
                    """
                    
                    vision_model = genai.GenerativeModel(self.model_name)
                    description_response = vision_model.generate_content([description_prompt, Image.open(design_path)])
                    description = description_response.text if hasattr(description_response, 'text') else f"A {style.lower()} house design optimized for Sikkim's mountain climate."
                    
                    designs.append({
                        'design_type': style,
                        'image_url': f"/static/upload/house_designs/{design_filename}",
                        'building_cost': building_cost,
                        'labor_cost': labor_cost,
                        'total_cost': total_cost,
                        'description': description
                    })
                    
                except Exception as e:
                    logger.error(f"Error generating design for style {style}: {str(e)}")
                    # Fallback to a simpler approach if the API call fails
                    designs.append({
                        'design_type': style,
                        'image_url': "",  # No image available
                        'building_cost': max_construction_budget * 0.7 if fund_allocation else 1000000,
                        'labor_cost': max_construction_budget * 0.3 if fund_allocation else 400000,
                        'total_cost': max_construction_budget if fund_allocation else 1400000,
                        'description': f"A {style.lower()} house design with optimal space utilization suited for Sikkim's climate and geography."
                    })
            
            return designs
            
        except Exception as e:
            logger.error(f"Error generating house designs: {str(e)}")
            raise
    
    def generate_detailed_design(self, design_id, original_design_data, comments=None):
        """
        Generate detailed interior, exterior views and blueprint for selected design
        
        Parameters:
        - design_id: ID of the selected design
        - original_design_data: Original design data from the database
        - comments: Any additional user comments/requests
        
        Returns:
        - Updated design data with interior, exterior and blueprint URLs
        """
        try:
            # Create directory for house designs if it doesn't exist
            designs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'house_designs')
            self._ensure_directory_exists(designs_dir)
            
            # Extract design style and other information
            design_style = original_design_data.get('design_type', 'Traditional')
            description = original_design_data.get('description', '')
            
            # Construct the path to the original design image
            original_image_url = original_design_data.get('image_url', '')
            original_image = None
            if original_image_url:
                original_image_filename = os.path.basename(original_image_url)
                # Assumes original images, if referenced by a URL, are also located within the designs_dir
                original_image_path = os.path.join(designs_dir, original_image_filename)
            
                if os.path.exists(original_image_path):
                    original_image = self._load_image_for_genai(original_image_path)
                else:
                    logger.warning(f"Original image not found at derived path: {original_image_path}. This might affect the quality of detailed design generation if the original image was intended as context.")
            
            if not original_image and original_image_url: # Log only if URL was present but image not found
                logger.warning("Proceeding with detailed design generation without the original image as context due to path mismatch or missing file.")
            elif not original_image_url:
                 logger.info("No original image URL provided for detailed design generation.")

            views = {
                'interior': {
                    'prompt': f"Generate a detailed interior view of the {design_style} house. {comments if comments else ''}",
                    'filename': f"interior_{uuid.uuid4().hex[:8]}.jpg"
                },
                'exterior': {
                    'prompt': f"Generate a detailed exterior view of the {design_style} house from a different angle. {comments if comments else ''}",
                    'filename': f"exterior_{uuid.uuid4().hex[:8]}.jpg"
                },
                'blueprint': {
                    'prompt': f"Generate a detailed floor plan/blueprint of the {design_style} house design. Show room layouts, dimensions, and key features. {comments if comments else ''}",
                    'filename': f"blueprint_{uuid.uuid4().hex[:8]}.jpg"
                }
            }
            
            results = {}
            generation_config = {
                "temperature": 0.7,
                "top_p": 1,
                "top_k": 32,
                "max_output_tokens": 2048,
                "response_mime_type": "image/jpeg"
            }
            
            model = genai.GenerativeModel(
                model_name=self.image_model,
                generation_config=generation_config
            )
            
            for view_type, view_data in views.items():
                try:
                    input_content = [view_data['prompt']]
                    if original_image:
                        input_content.append(original_image)
                    
                    response = model.generate_content(input_content)
                    
                    # Save the generated image
                    image_path = os.path.join(designs_dir, view_data['filename'])
                    
                    # Extract and save the image from the response
                    if hasattr(response, 'candidates') and len(response.candidates) > 0 and hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts'):
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'file_data') and hasattr(part.file_data, 'mime_type') and 'image' in part.file_data.mime_type:
                                with open(image_path, 'wb') as f:
                                    f.write(part.file_data.file_bytes)
                    
                    results[f'{view_type}_url'] = f"/static/upload/house_designs/{view_data['filename']}"
                except Exception as e:
                    logger.error(f"Error generating {view_type} view: {str(e)}")
                    results[f'{view_type}_url'] = ""
            
            # Generate enhanced description
            try:
                detail_prompt = f"""
                Based on the {design_style} house design and the following description:
                
                {description}
                
                Provide an enhanced, detailed description that includes information about:
                1. Interior layout and features
                2. Exterior materials and design elements
                3. Energy efficiency considerations
                4. Adaptations for Sikkim's climate
                
                Keep it concise but informative.
                """
                
                vision_model = genai.GenerativeModel(self.model_name)
                detail_response = vision_model.generate_content(detail_prompt)
                enhanced_description = detail_response.text if hasattr(detail_response, 'text') else description
                
                results['description'] = enhanced_description
            except Exception as e:
                logger.error(f"Error generating enhanced description: {str(e)}")
                results['description'] = description + "\n\nDetailed features include spacious living areas, energy-efficient design, and locally-sourced materials."
            
            return results
            
        except Exception as e:
            logger.error(f"Error generating detailed design: {str(e)}")
            raise

# The code uses the actual Gemini API SDK. 