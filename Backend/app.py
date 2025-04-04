from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import os
import logging
from datetime import timedelta
import json

# Import Services
from services.auth_service import AuthService
from services.document_service import DocumentService
from services.metadata_service import MetadataService
from services.vector_service import VectorService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object('config.Config')

# Enable CORS
CORS(app)

# Setup JWT
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
jwt = JWTManager(app)

# Initialize services
auth_service = AuthService()
document_service = DocumentService()
metadata_service = MetadataService()
vector_service = VectorService()

# Create upload directory if it doesn't exist
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'SciLit2.0 API is running'}), 200


# Authentication routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        required_fields = ['email', 'password', 'firstName', 'lastName']
        
        # Validate request data
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if user already exists
        if auth_service.get_user_by_email(data['email']):
            return jsonify({'error': 'User already exists'}), 409
        
        # Create new user
        user = auth_service.create_user(
            email=data['email'],
            password=data['password'],
            first_name=data['firstName'],
            last_name=data['lastName']
        )
        
        return jsonify({'message': 'User registered successfully'}), 201
    
    except Exception as e:
        logger.error(f"Error in register: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate a user and return a JWT token"""
    try:
        data = request.get_json()
        
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password required'}), 400
        
        user = auth_service.authenticate_user(data['email'], data['password'])
        
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Create access token
        access_token = create_access_token(identity=user['email'])
        
        return jsonify({
            'access_token': access_token,
            'user': {
                'email': user['email'],
                'firstName': user['first_name'],
                'lastName': user['last_name']
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error in login: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500


# Document routes
@app.route('/api/documents/upload', methods=['POST'])
@jwt_required()
def upload_document():
    """Upload a document and extract metadata"""
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and document_service.allowed_file(file.filename):
            user_email = get_jwt_identity()
            
            # Save the file temporarily
            file_path = document_service.save_file(file, UPLOAD_FOLDER)
            
            # Extract text with OCR
            text = document_service.extract_text(file_path)
            
            # Extract DOI/ISBN
            identifiers = metadata_service.extract_identifiers(text)
            
            # Fetch metadata from CrossRef or other sources
            metadata = metadata_service.fetch_metadata(identifiers)
            
            # Return the extracted metadata to the client for review
            return jsonify({
                'message': 'File uploaded successfully',
                'filePath': file_path,
                'metadata': metadata
            }), 200
        else:
            return jsonify({'error': 'File type not allowed'}), 400
    
    except Exception as e:
        logger.error(f"Error in upload_document: {str(e)}")
        return jsonify({'error': 'Document upload failed'}), 500


@app.route('/api/documents/save', methods=['POST'])
@jwt_required()
def save_document():
    """Save document with metadata to database and process for vector search"""
    try:
        data = request.get_json()
        user_email = get_jwt_identity()
        
        required_fields = ['filePath', 'metadata', 'chunkSize', 'chunkOverlap', 'citationStyle']
        
        # Validate request data
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Save metadata to database
        document_id = document_service.save_document_metadata(
            user_email=user_email,
            metadata=data['metadata']
        )
        
        # Move file from temp location to permanent storage
        permanent_path = document_service.move_to_permanent_storage(
            file_path=data['filePath'],
            document_id=document_id,
            user_email=user_email
        )
        
        # Process text into chunks
        text = document_service.extract_text(permanent_path)
        chunks = vector_service.create_chunks(
            text=text,
            chunk_size=data['chunkSize'],
            chunk_overlap=data['chunkOverlap']
        )
        
        # Store chunks in vector database
        vector_service.store_chunks(
            chunks=chunks,
            document_id=document_id,
            metadata=data['metadata']
        )
        
        return jsonify({
            'message': 'Document saved successfully',
            'documentId': document_id
        }), 200
    
    except Exception as e:
        logger.error(f"Error in save_document: {str(e)}")
        return jsonify({'error': 'Failed to save document'}), 500


@app.route('/api/documents', methods=['GET'])
@jwt_required()
def get_user_documents():
    """Get all documents for the authenticated user"""
    try:
        user_email = get_jwt_identity()
        documents = document_service.get_documents_by_user(user_email)
        
        return jsonify({
            'documents': documents
        }), 200
    
    except Exception as e:
        logger.error(f"Error in get_user_documents: {str(e)}")
        return jsonify({'error': 'Failed to retrieve documents'}), 500


@app.route('/api/documents/<document_id>', methods=['GET'])
@jwt_required()
def get_document(document_id):
    """Get a specific document by ID"""
    try:
        user_email = get_jwt_identity()
        document = document_service.get_document_by_id(document_id, user_email)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        return jsonify({
            'document': document
        }), 200
    
    except Exception as e:
        logger.error(f"Error in get_document: {str(e)}")
        return jsonify({'error': 'Failed to retrieve document'}), 500


@app.route('/api/documents/<document_id>', methods=['DELETE'])
@jwt_required()
def delete_document(document_id):
    """Delete a document"""
    try:
        user_email = get_jwt_identity()
        success = document_service.delete_document(document_id, user_email)
        
        if not success:
            return jsonify({'error': 'Document not found or you do not have permission'}), 404
        
        # Also remove from vector database
        vector_service.delete_document_chunks(document_id)
        
        return jsonify({
            'message': 'Document deleted successfully'
        }), 200
    
    except Exception as e:
        logger.error(f"Error in delete_document: {str(e)}")
        return jsonify({'error': 'Failed to delete document'}), 500


# AI query routes
@app.route('/api/query', methods=['POST'])
@jwt_required()
def query_documents():
    """Query documents using LLM and vector search"""
    try:
        data = request.get_json()
        user_email = get_jwt_identity()
        
        if 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        
        # Default to all user documents if no specific IDs are provided
        document_ids = data.get('documentIds', None)
        citation_style = data.get('citationStyle', 'apa7')
        
        # Perform vector search to find relevant chunks
        results = vector_service.search(
            query=data['query'],
            user_email=user_email,
            document_ids=document_ids
        )
        
        # Generate response with citations
        response = vector_service.generate_response_with_citations(
            query=data['query'],
            search_results=results,
            citation_style=citation_style
        )
        
        return jsonify({
            'response': response['answer'],
            'citations': response['citations'],
            'references': response['references']
        }), 200
    
    except Exception as e:
        logger.error(f"Error in query_documents: {str(e)}")
        return jsonify({'error': 'Query processing failed'}), 500


# Start the app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
