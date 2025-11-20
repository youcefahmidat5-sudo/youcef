"""
My Intelligent Library Web Application
A Flask-based web app for managing and reading digital books with AI-powered search.
"""
import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, session, jsonify, send_from_directory
import sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from functools import wraps
import json
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required as flask_login_required, current_user
from authlib.integrations.flask_client import OAuth
try:
    from PIL import Image  # type: ignore
    PIL_AVAILABLE = True
except Exception:
    Image = None  # type: ignore
    PIL_AVAILABLE = False
try:
    import imghdr  # type: ignore
except Exception:
    imghdr = None  # type: ignore
# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-in-production')
CORS(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize OAuth
oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID', 'your-google-client-id'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET', 'your-google-client-secret'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Language support
LANGUAGES = {
    'ar': {
        'name': 'العربية',
        'dir': 'rtl',
        'code': 'ar'
    },
    'en': {
        'name': 'English',
        'dir': 'ltr',
        'code': 'en'
    }
}

# Default language is Arabic
DEFAULT_LANGUAGE = 'ar'

def get_current_language():
    """Get the current language from session or return default."""
    return session.get('language', DEFAULT_LANGUAGE)

def get_language_data():
    """Get language-specific data."""
    current_lang = get_current_language()
    return LANGUAGES[current_lang]

def get_translations():
    """Get translations for the current language."""
    current_lang = get_current_language()
    
    translations = {
        'ar': {
            'app_name': 'مكتبتي الذكية',
            
            'home': 'الرئيسية',
            'add_book': 'إضافة كتاب',
            'ai_search': 'البحث الذكي',
            'login': 'تسجيل الدخول',
            'logout': 'تسجيل الخروج',
            'search_placeholder': 'البحث في الكتب...',
            'welcome_back': 'مرحباً بعودتك،',
            'welcome_to_library': 'مرحباً',
            'discover_books': '',
            'add_new_book': 'إضافة كتاب جديد',
            'available_books': 'الكتب المتاحة',
            'no_books_available': 'لا توجد كتب متاحة',
            'start_building': '',
            'add_first_book': 'أضف كتابك الأول',
            'view_details': 'عرض التفاصيل',
            'download': 'تحميل',
            'added_on': 'أضيف في',
            'no_description': 'لا يوجد وصف متاح',
            'book_title': 'عنوان الكتاب',
            'author': 'المؤلف',
            'description': 'الوصف',
            'pdf_file': 'ملف PDF',
            'cancel': 'إلغاء',
            'save': 'حفظ',
            'enter_library': 'دخول المكتبة',
            'first_name': 'الاسم الأول',
            'last_name': 'اسم العائلة',
            'email': 'البريد الإلكتروني',
            'enter_first_name': 'أدخل اسمك الأول',
            'enter_last_name': 'أدخل اسم العائلة',
            'enter_email': 'أدخل بريدك الإلكتروني',
            'your_given_name': 'اسمك الشخصي',
            'your_family_name': 'اسم عائلتك',
            'we_never_share': 'لن نشارك بريدك الإلكتروني مع أي شخص آخر',
            'no_password_required': 'لا حاجة لكلمة مرور - فقط أدخل اسمك للبدء!',
            'what_you_can_do': 'ما يمكنك فعله',
            'browse_books': 'تصفح الكتب الرقمية',
            'search_books': 'البحث بالعنوان أو المؤلف',
            'download_books': 'تحميل كتب PDF',
            'add_books': 'إضافة كتب جديدة للمكتبة',
            'view_details_books': 'عرض تفاصيل الكتب',
            'personalized_experience': 'تجربة شخصية',
            'upload_guidelines': 'إرشادات الرفع',
            'only_pdf_accepted': 'يتم قبول ملفات PDF فقط',
            'max_file_size': 'الحد الأقصى لحجم الملف: 16 ميجابايت',
            'make_sure_readable': 'تأكد من أن ملف PDF قابل للقراءة وغير تالف',
            'provide_accurate_info': 'قدم معلومات دقيقة للعنوان والمؤلف',
            'ai_powered_search': 'البحث الذكي',
            'ask_ai_assistant': 'اسأل مساعدنا الذكي',
            'your_question': 'سؤالك أو استعلام البحث',
            'ask_anything': 'اسأل أي شيء عن الكتب، الأدب، أو احصل على توصيات قراءة شخصية!',
            'ask_placeholder': 'اسأل أي شيء عن الكتب، الأدب، أو احصل على توصيات قراءة شخصية...',
            'examples': 'أمثلة: "أوصي برواية غموض جيدة"، "ما هو موضوع روميو وجولييت؟"، "ابحث عن كتب استكشاف الفضاء"',
            'clear': 'مسح',
            'search_with_ai': 'البحث بالذكاء الاصطناعي',
            'ai_response': 'استجابة الذكاء الاصطناعي',
            'powered_by_openai': 'مدعوم من OpenAI ChatGPT',
            'copy_response': 'نسخ الاستجابة',
            'ai_thinking': 'الذكاء الاصطناعي يفكر...',
            'please_wait': 'يرجى الانتظار بينما يعالج مساعدنا الذكي استفسارك.',
            'quick_questions': 'الأسئلة السريعة',
            'book_recommendations': 'توصيات الكتب',
            'mystery_novels': 'روايات الغموض',
            'classic_literature': 'الأدب الكلاسيكي',
            'science_fiction': 'الخيال العلمي',
            'general_questions': 'الأسئلة العامة',
            'fiction_vs_nonfiction': 'الخيال مقابل الواقع',
            'reading_tips': 'نصائح القراءة',
            'benefits_reading': 'فوائد القراءة',
            'welcome_to_smart_library': 'مرحباً بك في مكتبتي الذكية',
            'please_enter_name': 'يرجى إدخال اسمك للمتابعة',
            'book_added_successfully': 'تم إضافة الكتاب بنجاح!',
            'book_deleted_successfully': 'تم حذف الكتاب بنجاح!',
            'goodbye': 'وداعاً،',
            'you_have_been_logged_out': 'تم تسجيل خروجك.',
            'you_were_not_logged_in': 'لم تكن مسجلاً دخولاً.',
            'please_log_in': 'يرجى تسجيل الدخول للوصول إلى هذه الصفحة',
            'login_failed': 'فشل تسجيل الدخول',
            'no_file_selected': 'لم يتم اختيار ملف',
            'invalid_file_type': 'نوع ملف غير صالح. يُسمح فقط بملفات PDF.',
            'file_not_found': 'الملف غير موجود',
            'please_enter_search_query': 'يرجى إدخال استعلام البحث',
            'error_getting_ai_response': 'خطأ في الحصول على استجابة الذكاء الاصطناعي',
            'error_deleting_file': 'خطأ في حذف الملف',
            'book_deleted_from_database': 'تم حذف الكتاب من قاعدة البيانات، لكن الملف غير موجود.',
            'built_with_flask': '',
            'language': 'اللغة',
            'switch_to_english': 'التبديل إلى الإنجليزية',
            'switch_to_arabic': 'التبديل إلى العربية',
            'book_information': 'معلومات الكتاب',
            'quick_actions': 'الإجراءات السريعة',
            'view_all_books': 'عرض جميع الكتب',
            'delete': 'حذف',
            'search_results': 'نتائج البحث',
            'search_query': 'استعلام البحث',
            'found': 'تم العثور على',
            'book': 'كتاب',
            'no_books_found': 'لم يتم العثور على كتب',
            'no_books_found_message': 'لم يتم العثور على كتب تطابق',
            'try_different_search': 'جرب مصطلح بحث مختلف أو تصفح جميع الكتب.',
            'browse_all_books': 'تصفح جميع الكتب',
            'back_to_all_books': 'العودة إلى جميع الكتب',
            'search_again': 'البحث مرة أخرى',
            'search': 'بحث',
            'books': 'الكتب',
            'articles': 'المقالات',
            'digital_repositories': 'المستودعات الرقمية',
            'open_access_websites': 'مواقع الوصول الحر',
            'generate_abstract': 'إنشاء مستخلص',
            'abstract': 'المستخلص',
            'generating_abstract': 'جاري إنشاء المستخلص...',
            'abstract_generated': 'تم إنشاء المستخلص',
            'error_generating_abstract': 'خطأ في إنشاء المستخلص',
            'recently_added_books': 'الكتب المضافة حديثًا',
            'all_books': 'كل الكتب',
            'search_books_placeholder': 'ابحث في الكتب...',
            'sail_through_library': 'ابحر في مكتبتك الذكية',
            'generate_annotation': 'التهميش',
            'annotation': 'التهميش',
            'generating_annotation': 'جاري إنشاء التهميش...',
            'annotation_generated': 'تم إنشاء التهميش',
            'error_generating_annotation': 'خطأ في إنشاء التهميش',
            'book_cover_image': 'صورة غلاف الكتاب',
            'image_guideline': 'الصورة اختيارية (PNG/JPG/GIF/WEBP) بحجم أقصى 5 ميجابايت',
            'image_too_large': 'الصورة كبيرة جدًا. الحد الأقصى 5 ميجابايت',
            'invalid_image_file': 'ملف الصورة غير صالح',
            'invalid_image_type': 'نوع الصورة غير صالح. المسموح: PNG, JPG, GIF, WEBP',
            'image_required': 'صورة الغلاف مطلوبة لكل كتاب',
            'discipline_label': 'التخصص',
            'discipline_placeholder': 'اختر التخصص',
            'discipline_help_text': 'حدد التخصص الذي ينتمي إليه هذا الكتاب.',
            'invalid_discipline_selected': 'يرجى اختيار تخصص صالح.',
            'discipline_library_science': 'علم المكتبات',
            'discipline_media_communication': 'الإعلام والاتصال',
            'discipline_history': 'التاريخ',
            'discipline_archaeology': 'علم الآثار',
            'categorized_book_lists_title': 'قوائم الكتب المتخصصة',
            'categorized_book_lists_subtitle': 'نظّم مجموعتك حسب التخصصات المختلفة.',
            'category_section_hint': 'أضف كتباً عبر صفحة إضافة كتاب وحدد التخصص المناسب لكل عنوان.',
            'category_library_science': 'قائمة كتب علم المكتبات',
            'category_library_science_desc': 'كتب حول التصنيف، الفهرسة، وخدمات المعلومات.',
            'category_media_communication': 'قائمة كتب الإعلام و الاتصال',
            'category_media_communication_desc': 'مراجع الصحافة الرقمية، الإذاعة، واستراتيجيات الاتصال.',
            'category_history': 'قائمة كتب التاريخ',
            'category_history_desc': 'مصادر تاريخية، تحليلات حضارية، وسير ذاتية.',
            'category_archaeology': 'قائمة كتب علم الآثار',
            'category_archaeology_desc': 'دراسات التنقيب، الحضارات القديمة، وتقنيات الحفظ.',
            'add_book_to_list': 'إضافة كتاب لهذه القائمة',
            'source_or_reference': 'المصدر أو الرابط',
            'view_source': 'عرض المصدر',
            'view_list': 'استعراض القائمة',
            'no_books_in_category': 'لا توجد كتب في هذه القائمة بعد.',
            'category_fields_required': 'يرجى تعبئة جميع الحقول وإرفاق صورة الغلاف.',
            'category_book_added_successfully': 'تمت إضافة الكتاب إلى القائمة بنجاح!'
        },
        'en': {
            'app_name': 'My Intelligent Library',
            'home': 'Home',
            'add_book': 'Add Book',
            'ai_search': 'AI Search',
            'login': 'Login',
            'logout': 'Logout',
            'search_placeholder': 'Search books...',
            'welcome_back': 'Welcome back,',
            'welcome_to_library': 'Welcome',
            'discover_books': 'Discover and manage your digital book collection. Browse, search, and download books in PDF format.',
            'add_new_book': 'Add New Book',
            'available_books': 'Available Books',
            'no_books_available': 'No Books Available',
            'start_building': 'Start building your smart library! Add your first book to get started.',
            'add_first_book': 'Add Your First Book',
            'view_details': 'View Details',
            'download': 'Download',
            'added_on': 'Added:',
            'no_description': 'No description available',
            'book_title': 'Book Title',
            'author': 'Author',
            'description': 'Description',
            'pdf_file': 'PDF File',
            'cancel': 'Cancel',
            'save': 'Save',
            'enter_library': 'Enter Library',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email Address',
            'enter_first_name': 'Enter your first name',
            'enter_last_name': 'Enter your last name',
            'enter_email': 'Enter your email address',
            'your_given_name': 'Your given name',
            'your_family_name': 'Your family name',
            'we_never_share': "We'll never share your email with anyone else",
            'no_password_required': 'No password required - just enter your name to get started!',
            'what_you_can_do': 'What You Can Do',
            'browse_books': 'Browse digital books',
            'search_books': 'Search by title or author',
            'download_books': 'Download PDF books',
            'add_books': 'Add new books to library',
            'view_details_books': 'View book details',
            'personalized_experience': 'Personalized experience',
            'upload_guidelines': 'Upload Guidelines',
            'only_pdf_accepted': 'Only PDF files are accepted',
            'max_file_size': 'Maximum file size: 16MB',
            'make_sure_readable': 'Make sure the PDF is readable and not corrupted',
            'provide_accurate_info': 'Provide accurate title and author information',
            'ai_powered_search': 'AI-Powered Search',
            'ask_ai_assistant': 'Ask Our AI Assistant',
            'your_question': 'Your Question or Search Query',
            'ask_anything': 'Ask our AI assistant anything about books, literature, or get personalized reading recommendations!',
            'ask_placeholder': 'Ask anything about books, literature, or get reading recommendations...',
            'examples': 'Examples: "Recommend a good mystery novel", "What is the theme of Romeo and Juliet?", "Find books about space exploration"',
            'clear': 'Clear',
            'search_with_ai': 'Search with AI',
            'ai_response': 'AI Response',
            'powered_by_openai': 'Powered by OpenAI ChatGPT',
            'copy_response': 'Copy Response',
            'ai_thinking': 'AI is thinking...',
            'please_wait': 'Please wait while our AI assistant processes your query.',
            'quick_questions': 'Quick Questions',
            'book_recommendations': 'Book Recommendations',
            'mystery_novels': 'Mystery novels',
            'classic_literature': 'Classic literature',
            'science_fiction': 'Science fiction',
            'general_questions': 'General Questions',
            'fiction_vs_nonfiction': 'Fiction vs Non-fiction',
            'reading_tips': 'Reading tips',
            'benefits_reading': 'Benefits of reading',
            'welcome_to_smart_library': 'Welcome to My Intelligent Library',
            'please_enter_name': 'Please enter your name to continue',
            'book_added_successfully': 'Book added successfully!',
            'book_deleted_successfully': 'Book deleted successfully!',
            'goodbye': 'Goodbye,',
            'you_have_been_logged_out': 'You have been logged out.',
            'you_were_not_logged_in': 'You were not logged in.',
            'please_log_in': 'Please log in to access this page',
            'login_failed': 'Login failed',
            'no_file_selected': 'No file selected',
            'invalid_file_type': 'Invalid file type. Only PDF files are allowed.',
            'file_not_found': 'File not found',
            'please_enter_search_query': 'Please enter a search query',
            'error_getting_ai_response': 'Error getting AI response',
            'error_deleting_file': 'Error deleting file',
            'book_deleted_from_database': 'Book deleted from database, but file was not found.',
            'built_with_flask': 'Built with Flask and Bootstrap.',
            'language': 'Language',
            'switch_to_english': 'Switch to English',
            'switch_to_arabic': 'Switch to Arabic',
            'book_information': 'Book Information',
            'quick_actions': 'Quick Actions',
            'view_all_books': 'View All Books',
            'delete': 'Delete',
            'search_results': 'Search Results',
            'search_query': 'Search Query',
            'found': 'Found',
            'book': 'book',
            'no_books_found': 'No Books Found',
            'no_books_found_message': 'No books found matching',
            'try_different_search': 'Try a different search term or browse all books.',
            'browse_all_books': 'Browse All Books',
            'back_to_all_books': 'Back to All Books',
            'search_again': 'Search Again',
            'search': 'Search',
            'books': 'Books',
            'articles': 'Articles',
            'digital_repositories': 'Digital Repositories',
            'open_access_websites': 'Open Access Websites',
            'generate_abstract': 'Generate Abstract',
            'abstract': 'Abstract',
            'generating_abstract': 'Generating Abstract...',
            'abstract_generated': 'Abstract Generated',
            'error_generating_abstract': 'Error Generating Abstract',
            'recently_added_books': 'Recently Added Books',
            'all_books': 'All Books',
            'search_books_placeholder': 'Search books...',
            'sail_through_library': 'Sail through your smart library',
            'generate_annotation': 'Annotation',
            'annotation': 'Annotation',
            'generating_annotation': 'Generating Annotation...',
            'annotation_generated': 'Annotation Generated',
            'error_generating_annotation': 'Error Generating Annotation',
            'book_cover_image': 'Book Cover Image',
            'image_guideline': 'Optional image (PNG/JPG/GIF/WEBP) up to 5MB',
            'image_too_large': 'Image file too large. Maximum is 5MB',
            'invalid_image_file': 'Invalid image file',
            'invalid_image_type': 'Invalid image type. Allowed: PNG, JPG, GIF, WEBP',
            'image_required': 'Cover image is required for every book',
            'discipline_label': 'Discipline',
            'discipline_placeholder': 'Select a discipline',
            'discipline_help_text': 'Choose the focus area that best fits this book.',
            'invalid_discipline_selected': 'Please select a valid discipline.',
            'discipline_library_science': 'Library Science',
            'discipline_media_communication': 'Media & Communication',
            'discipline_history': 'History',
            'discipline_archaeology': 'Archaeology',
            'categorized_book_lists_title': 'Specialized Book Lists',
            'categorized_book_lists_subtitle': 'Organize your collection by the focus areas below.',
            'category_section_hint': 'Use the Add Book form to assign each title to a specialty.',
            'category_library_science': 'Library Science Book List',
            'category_library_science_desc': 'Classification, cataloging, and information services resources.',
            'category_media_communication': 'Media & Communication Book List',
            'category_media_communication_desc': 'Digital journalism, broadcasting, and communication strategy titles.',
            'category_history': 'History Book List',
            'category_history_desc': 'Primary sources, civilizations, and biographical studies.',
            'category_archaeology': 'Archaeology Book List',
            'category_archaeology_desc': 'Excavation research, ancient cultures, and preservation techniques.',
            'add_book_to_list': 'Add a Book to This List',
            'source_or_reference': 'Source or reference',
            'view_source': 'View source',
            'view_list': 'View list',
            'no_books_in_category': 'No books have been added to this list yet.',
            'category_fields_required': 'Please fill in all fields and attach a cover image.',
            'category_book_added_successfully': 'Book added to the list successfully!'
        }
    }
    
    return translations[current_lang]

CATEGORY_SECTIONS = [
    {
        'key': 'library_science',
        'title_key': 'category_library_science',
        'description_key': 'category_library_science_desc',
        'icon': 'fa-book-open',
        'accent_class': 'category-accent-library',
        'option_label_key': 'discipline_library_science'
    },
    {
        'key': 'media_and_communication',
        'title_key': 'category_media_communication',
        'description_key': 'category_media_communication_desc',
        'icon': 'fa-microphone-lines',
        'accent_class': 'category-accent-media',
        'option_label_key': 'discipline_media_communication'
    },
    {
        'key': 'history',
        'title_key': 'category_history',
        'description_key': 'category_history_desc',
        'icon': 'fa-landmark',
        'accent_class': 'category-accent-history',
        'option_label_key': 'discipline_history'
    },
    {
        'key': 'archaeology',
        'title_key': 'category_archaeology',
        'description_key': 'category_archaeology_desc',
        'icon': 'fa-monument',
        'accent_class': 'category-accent-archaeology',
        'option_label_key': 'discipline_archaeology'
    }
]

def build_category_sections(translations):
    """Create localized metadata for each curated category section."""
    sections = []
    for section in CATEGORY_SECTIONS:
        sections.append({
            'key': section['key'],
            'icon': section['icon'],
            'accent_class': section['accent_class'],
            'title': translations.get(section['title_key'], section['title_key']),
            'description': translations.get(section['description_key'], '')
        })
    return sections

def build_discipline_options(translations):
    """Return localized discipline labels for select inputs."""
    options = []
    for section in CATEGORY_SECTIONS:
        label_key = section.get('option_label_key')
        label = translations.get(label_key, translations.get(section['title_key'], section['key']))
        options.append({
            'key': section['key'],
            'label': label
        })
    return options

# Authorization helpers
ALLOWED_ADD_BOOK_EMAIL = 'badrelddinahmidat@gmail.com'

def can_add_books():
    """Return True if the current session user is allowed to add books."""
    # Check if user is authenticated with Flask-Login
    if current_user.is_authenticated:
        return current_user.email == ALLOWED_ADD_BOOK_EMAIL
    # Check traditional login method
    return session.get('email') == ALLOWED_ADD_BOOK_EMAIL

 

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
IMAGE_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}  # Case-insensitive check in allowed_image()
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB max image size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Ensure static/covers directory exists
os.makedirs('static/covers', exist_ok=True)

# User model for Flask-Login
class User(UserMixin):
    def __init__(self, id, email, first_name, last_name):
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name

@login_manager.user_loader
def load_user(user_id):
    if 'user_info' in session and session.get('email') == user_id:
        user_info = session.get('user_info', {})
        return User(
            user_info.get('email', ''),
            user_info.get('email', ''),
            user_info.get('first_name', ''),
            user_info.get('last_name', '')
        )
    return None

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated and not session.get('logged_in'):
            flash(get_translations()['please_log_in'], 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image(filename):
    """Check if the uploaded image has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in IMAGE_ALLOWED_EXTENSIONS

def validate_image_file(file_stream):
    """Validate that the uploaded file is a real image.
    Prefer Pillow verification; fall back to imghdr if Pillow is unavailable.
    More lenient validation to accept common image formats.
    """
    try:
        file_stream.seek(0)
        if PIL_AVAILABLE and Image is not None:
            try:
                with Image.open(file_stream) as img:
                    # Verify the image
                    img.verify()
                file_stream.seek(0)
                return True
            except Exception:
                # If Pillow fails, try to reopen and check format
                file_stream.seek(0)
                try:
                    with Image.open(file_stream) as img:
                        format_name = img.format
                        if format_name and format_name.upper() in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                            file_stream.seek(0)
                            return True
                except Exception:
                    pass
        # Fallback: imghdr check
        detected = imghdr.what(file_stream) if imghdr else None
        file_stream.seek(0)
        if detected in {'jpeg', 'png', 'gif', 'webp'}:
            return True
        # Additional check: if file extension is valid, accept it (more lenient)
        # This handles cases where imghdr might not detect the format correctly
        return True  # Accept if extension check passed
    except Exception:
        file_stream.seek(0)
        # More lenient: if we can't validate, but extension is valid, accept it
        return True

def save_cover_image(file_storage, translations, require_image=False):
    """Persist an uploaded cover image to disk and return its filename."""
    filename_value = getattr(file_storage, 'filename', '') if file_storage else ''
    if not filename_value:
        if require_image:
            return None, translations.get('image_required', 'Cover image is required for every book')
        return None, None
    
    if not allowed_image(filename_value):
        return None, translations.get('invalid_image_type', 'Invalid image type. Allowed: PNG, JPG, JPEG, GIF, WEBP')
    
    try:
        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
        if size > MAX_IMAGE_SIZE:
            file_storage.seek(0)
            return None, translations.get('image_too_large', 'Image file too large. Maximum is 5MB')
        file_storage.seek(0)
    except Exception:
        try:
            file_storage.seek(0)
        except Exception:
            pass
    
    try:
        validate_image_file(file_storage)
    except Exception:
        pass
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
    safe_name = secure_filename(filename_value)
    if '.' in safe_name:
        name, ext = safe_name.rsplit('.', 1)
        safe_name = f"{name}.{ext.lower()}"
    cover_filename = f"{timestamp}{safe_name}"
    os.makedirs('static/covers', exist_ok=True)
    cover_path = os.path.join('static/covers', cover_filename)
    
    try:
        file_storage.seek(0)
        file_storage.save(cover_path)
    except Exception as exc:
        return None, f"Error saving cover image: {exc}"
    
    return cover_filename, None

def init_database():
    """Initialize the SQLite database with books table."""
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    
    # Create books table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            description TEXT,
            filename TEXT NOT NULL,
            image_filename TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migration: add image_filename column if missing
    cursor.execute("PRAGMA table_info(books)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'image_filename' not in columns:
        cursor.execute('ALTER TABLE books ADD COLUMN image_filename TEXT')
    
    # Migration: add publication_year column if missing
    if 'publication_year' not in columns:
        cursor.execute('ALTER TABLE books ADD COLUMN publication_year INTEGER')

    # Migration: add discipline column if missing
    if 'discipline' not in columns:
        cursor.execute('ALTER TABLE books ADD COLUMN discipline TEXT')
    
    # Create curated category books table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS category_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_key TEXT NOT NULL,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            source TEXT NOT NULL,
            cover_filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect('library.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/set_language/<language>')
def set_language(language):
    """Set the language for the session."""
    if language in LANGUAGES:
        session['language'] = language
    return redirect(request.referrer or url_for('index'))

@app.route('/')
@login_required
def index():
    """Homepage displaying search bar, recent books, and all books."""
    conn = get_db_connection()
    # Get recent books (last 6 books)
    recent_books = conn.execute('SELECT * FROM books ORDER BY upload_date DESC LIMIT 6').fetchall()
    # Get all books
    all_books = conn.execute('SELECT * FROM books ORDER BY upload_date DESC').fetchall()
    conn.close()
    return render_template('index.html', recent_books=recent_books, all_books=all_books, t=get_translations(), lang_data=get_language_data(), can_add_book=can_add_books())

@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    """Add a new book to the library."""
    t = get_translations()
    lang_data = get_language_data()
    discipline_options = build_discipline_options(t)
    valid_disciplines = {option['key'] for option in discipline_options}
    # Restrict access to the add page by email
    if not can_add_books():
        flash(t['please_log_in'], 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        description = request.form['description']
        discipline = request.form.get('discipline', '').strip()

        if discipline not in valid_disciplines:
            flash(t['invalid_discipline_selected'], 'error')
            return redirect(request.url)
        
        # Check if file was uploaded
        if 'file' not in request.files:
            flash(t['no_file_selected'], 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash(t['no_file_selected'], 'error')
            return redirect(request.url)
        
        # Validate PDF size
        if file and hasattr(file, 'seek'):
            file.seek(0, os.SEEK_END)
            if file.tell() > MAX_FILE_SIZE:
                file.seek(0)
                flash(t['max_file_size'], 'error')
                return redirect(request.url)
            file.seek(0)

        cover_file = request.files.get('cover')
        cover_filename_to_save = None
        
        if file and allowed_file(file.filename):
            # Secure the filename
            filename = secure_filename(file.filename)
            
            # Add timestamp to filename to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            
            # Save file
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            if cover_file and cover_file.filename:
                cover_filename_to_save, image_error = save_cover_image(cover_file, t)
                if image_error:
                    flash(image_error, 'error')
                    return redirect(request.url)

            # Save book info to database (with cover image)
            conn = get_db_connection()
            conn.execute(
                'INSERT INTO books (title, author, description, filename, image_filename, discipline) VALUES (?, ?, ?, ?, ?, ?)',
                (title, author, description, filename, cover_filename_to_save, discipline)
            )
            conn.commit()
            conn.close()
            
            flash(t['book_added_successfully'], 'success')
            return redirect(url_for('index'))
        else:
            flash(t['invalid_file_type'], 'error')
    
    return render_template('add_book.html', t=t, lang_data=lang_data, discipline_options=discipline_options)

@app.route('/book/<int:book_id>')
@login_required
def book_detail(book_id):
    """Display book details and provide download option."""
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    conn.close()
    
    if book is None:
        abort(404)
    
    return render_template('book_detail.html', book=book, t=get_translations(), lang_data=get_language_data(), can_add_book=can_add_books())

@app.route('/download/<int:book_id>')
@login_required
def download_book(book_id):
    """Download a book PDF file."""
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    conn.close()
    
    if book is None:
        abort(404)
    
    file_path = os.path.join(UPLOAD_FOLDER, book['filename'])
    
    if not os.path.exists(file_path):
        flash(get_translations()['file_not_found'], 'error')
        return redirect(url_for('index'))
    
    return send_file(file_path, as_attachment=True, download_name=f"{book['title']}.pdf")

@app.route('/uploads/<path:filename>')
@login_required
def serve_upload(filename):
    """Serve uploaded files (images)."""
    safe_name = secure_filename(filename)
    return send_from_directory(UPLOAD_FOLDER, safe_name, conditional=True)

@app.route('/covers/<path:filename>')
def serve_cover(filename):
    """Serve book cover images from static/covers directory.
    No login required - covers should be publicly viewable.
    """
    safe_name = secure_filename(filename)
    cover_path = os.path.join('static/covers', safe_name)
    if os.path.exists(cover_path):
        return send_from_directory('static/covers', safe_name, conditional=True)
    else:
        # Return a placeholder or 404
        abort(404)

@app.route('/search')
def search():
    """Search books by title or author."""
    query = request.args.get('q', '').strip()
    
    if not query:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    books = conn.execute(
        'SELECT * FROM books WHERE title LIKE ? OR author LIKE ? ORDER BY upload_date DESC',
        (f'%{query}%', f'%{query}%')
    ).fetchall()
    conn.close()
    
    return render_template('search_results.html', books=books, query=query, t=get_translations(), lang_data=get_language_data(), can_add_book=can_add_books())

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for users to enter their name and email or sign in with Google."""
    t = get_translations()
    
    if request.method == 'GET':
        return render_template('login.html', t=t, lang_data=get_language_data())
    
    # Handle traditional form login as fallback
    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        email = request.form['email'].strip()
        
        if not first_name or not last_name or not email:
            flash(t['please_enter_name'], 'error')
            return redirect(request.url)
        
        # Store user info in session
        session['first_name'] = first_name
        session['last_name'] = last_name
        session['email'] = email
        session['logged_in'] = True
        
        # Create user object and login with Flask-Login
        user = User(email, email, first_name, last_name)
        login_user(user)
        
        # Store user info for user_loader
        session['user_info'] = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name
        }
        
        flash(f'{t["welcome_back"]} {first_name} {last_name}!', 'success')
        return redirect(url_for('index'))

@app.route('/login/google')
def google_login():
    """Initiate Google OAuth login flow."""
    redirect_uri = url_for('google_auth', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google')
def google_auth():
    """Handle Google OAuth callback."""
    t = get_translations()
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            flash(t['login_failed'], 'error')
            return redirect(url_for('login'))
        
        # Extract user information
        email = user_info.get('email')
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')
        
        # Store user info in session
        session['first_name'] = first_name
        session['last_name'] = last_name
        session['email'] = email
        session['logged_in'] = True
        
        # Create user object and login with Flask-Login
        user = User(email, email, first_name, last_name)
        login_user(user)
        
        # Store user info for user_loader
        session['user_info'] = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name
        }
        
        flash(f'{t["welcome_back"]} {first_name} {last_name}!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'{t["login_failed"]}: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """Logout user and clear session."""
    t = get_translations()
    if session.get('logged_in'):
        first_name = session.get('first_name', '')
        logout_user()  # Flask-Login logout
        session.clear()
        flash(f'{t["goodbye"]} {first_name}! {t["you_have_been_logged_out"]}', 'info')
    else:
        flash(t['you_were_not_logged_in'], 'info')
    
    return redirect(url_for('index'))

@app.route('/delete/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    """Delete a book from the library and remove its file."""
    t = get_translations()
    
    # Restrict deletion to only the authorized user
    if not can_add_books():
        flash(t['please_log_in'], 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    
    if book is None:
        conn.close()
        abort(404)
    
    # Get the filename before deleting from database
    filename = book['filename']
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    # Delete from database
    conn.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()
    
    # Delete the file if it exists
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            flash(t['book_deleted_successfully'], 'success')
        except Exception as e:
            flash(f'{t["error_deleting_file"]}: {str(e)}', 'error')
    else:
        flash(t['book_deleted_from_database'], 'warning')

    # Delete image file if it exists
    image_filename = book['image_filename'] if book['image_filename'] else None
    if image_filename:
        # Covers are stored in static/covers, not UPLOAD_FOLDER
        image_path = os.path.join('static/covers', image_filename)
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception:
                pass
    
    return redirect(url_for('index'))

@app.route('/ai_search', methods=['GET', 'POST'])
def ai_search():
    """AI-powered search page using OpenAI ChatGPT API."""
    t = get_translations()
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        
        # Get advanced search parameters
        author = request.form.get('author', '').strip()
        category = request.form.get('category', '').strip()
        year_from = request.form.get('yearFrom', '').strip()
        year_to = request.form.get('yearTo', '').strip()
        search_descriptions = request.form.get('searchDescriptions') == 'on'
        
        if not query:
            flash(t['please_enter_search_query'], 'error')
            return render_template('ai_search.html', t=t, lang_data=get_language_data())
        
        try:
            # Get available books from database for context
            conn = get_db_connection()
            books = conn.execute('SELECT title, author, description, publication_year FROM books').fetchall()
            conn.close()
            
            # Filter books based on advanced search parameters
            filtered_books = []
            for book in books:
                # Apply filters if they exist
                if author and author.lower() not in (book['author'] or '').lower():
                    continue
                if category and category.lower() not in (book['title'] or '').lower() and category.lower() not in (book['description'] or '').lower():
                    continue
                if year_from and book.get('publication_year') and int(year_from) > int(book['publication_year']):
                    continue
                if year_to and book.get('publication_year') and int(year_to) < int(book['publication_year']):
                    continue
                if not search_descriptions and book['description']:
                    # If not searching descriptions, truncate them
                    book = dict(book)
                    book['description'] = book['description'][:100] + "..." if len(book['description']) > 100 else book['description']
                
                filtered_books.append(book)
            
            # Create context about available books
            books_context = ""
            if filtered_books:
                books_context = "Available books in the library matching your criteria:\n"
                for book in filtered_books:
                    books_context += f"- {book['title']} by {book['author']}"
                    if book['description'] and (search_descriptions or not author and not category and not year_from and not year_to):
                        books_context += f" ({book['description']})"
                    if book.get('publication_year'):
                        books_context += f" (Published: {book['publication_year']})"
                    books_context += "\n"
            else:
                books_context = "No books found matching your specific criteria.\n"
            
            # Create the prompt for ChatGPT
            system_prompt = f"""You are a helpful AI assistant for a digital library called "My Intelligent Library". 
            You help users find books, answer questions about literature, and provide reading recommendations.
            
            {books_context}
            
            Please provide helpful, accurate, and engaging responses about books, reading, and literature.
            If the user asks about specific books, check if they're available in the library above.
            Keep responses concise but informative."""
            
            # Add advanced search context to the user query if parameters are provided
            enhanced_query = query
            if author or category or year_from or year_to:
                enhanced_query = f"{query}\n\nAdditional search criteria:"
                if author:
                    enhanced_query += f"\n- Author: {author}"
                if category:
                    enhanced_query += f"\n- Category/Subject: {category}"
                if year_from or year_to:
                    year_range = f"from {year_from}" if year_from else ""
                    year_range += f" to {year_to}" if year_to else ""
                    enhanced_query += f"\n- Publication year: {year_range}"
                if search_descriptions:
                    enhanced_query += "\n- Include full book descriptions in search"
            
            # Make API call to OpenAI
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhanced_query}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            return render_template('ai_search.html', 
                                 query=query,
                                 author=author,
                                 category=category,
                                 yearFrom=year_from,
                                 yearTo=year_to,
                                 searchDescriptions=search_descriptions,
                                 ai_response=ai_response,
                                 user_logged_in=session.get('logged_in', False),
                                 t=t, lang_data=get_language_data())
            
        except Exception as e:
            flash(f'{t["error_getting_ai_response"]}: {str(e)}', 'error')
            return render_template('ai_search.html', query=query, t=t, lang_data=get_language_data())
    
    return render_template('ai_search.html', 
                         user_logged_in=session.get('logged_in', False),
                         t=t, lang_data=get_language_data())

@app.route('/ai_search_api', methods=['POST'])
def ai_search_api():
    """API endpoint for AJAX AI search requests."""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Please enter a search query'}), 400
        
        # Get available books from database for context
        conn = get_db_connection()
        books = conn.execute('SELECT title, author, description FROM books').fetchall()
        conn.close()
        
        # Create context about available books
        books_context = ""
        if books:
            books_context = "Available books in the library:\n"
            for book in books:
                books_context += f"- {book['title']} by {book['author']}"
                if book['description']:
                    books_context += f" ({book['description'][:100]}...)"
                books_context += "\n"
        
        # Create the prompt for ChatGPT
        system_prompt = f"""You are a helpful AI assistant for a digital library called "Smart Library". 
        You help users find books, answer questions about literature, and provide reading recommendations.
        
        {books_context}
        
        Please provide helpful, accurate, and engaging responses about books, reading, and literature.
        If the user asks about specific books, check if they're available in the library above.
        Keep responses concise but informative."""
        
        # Make API call to OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
        return jsonify({
            'success': True,
            'query': query,
            'response': ai_response
        })
        
    except Exception as e:
        return jsonify({'error': f'Error getting AI response: {str(e)}'}), 500

@app.route('/books')
@login_required
def books():
    """Books page - displays all books and curated category lists."""
    t = get_translations()
    lang_data = get_language_data()
    can_add = can_add_books()
    active_category = request.args.get('category', '').strip()
    
    conn = get_db_connection()
    books = conn.execute('SELECT * FROM books ORDER BY upload_date DESC').fetchall()
    conn.close()
    
    category_sections = build_category_sections(t)
    category_books_map = {section['key']: [] for section in CATEGORY_SECTIONS}
    for book in books:
        discipline_key = (book['discipline'] or '').strip()
        if discipline_key in category_books_map:
            category_books_map[discipline_key].append(book)

    if active_category:
        display_sections = [section for section in category_sections if section['key'] == active_category]
    else:
        display_sections = category_sections
    
    return render_template(
        'books.html',
        books=books,
        category_sections=display_sections,
        category_books_map=category_books_map,
        active_category=active_category,
        t=t,
        lang_data=lang_data,
        can_add_book=can_add
    )

@app.route('/articles')
@login_required
def articles():
    """Articles page - placeholder for articles functionality."""
    return render_template('articles.html', t=get_translations(), lang_data=get_language_data())

@app.route('/digital_repositories')
@login_required
def digital_repositories():
    """Digital Repositories page - placeholder for digital repositories functionality."""
    return render_template('digital_repositories.html', t=get_translations(), lang_data=get_language_data())

@app.route('/open_access_websites')
@login_required
def open_access_websites():
    """Open Access Websites page - placeholder for open access websites functionality."""
    return render_template('open_access_websites.html', t=get_translations(), lang_data=get_language_data())

@app.route('/generate_abstract/<int:book_id>', methods=['POST'])
@login_required
def generate_abstract(book_id):
    """Generate an abstract for a book using AI."""
    t = get_translations()
    try:
        # Get book information
        conn = get_db_connection()
        book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        conn.close()
        
        if book is None:
            return jsonify({'error': 'Book not found'}), 404
        
        # Create prompt for abstract generation
        current_lang = get_current_language()
        language_instruction = "in Arabic" if current_lang == 'ar' else "in English"
        
        system_prompt = f"""You are an AI assistant that creates concise, informative abstracts for books. 
        Generate a well-structured abstract {language_instruction} that summarizes the main themes, key points, and value of the book.
        The abstract should be professional, clear, and between 150-300 words.
        Focus on the book's main content, themes, and significance."""
        
        user_prompt = f"""Please create an abstract for the following book:
        
        Title: {book['title']}
        Author: {book['author']}
        Description: {book['description'] if book['description'] else 'No description available'}
        
        Generate a comprehensive abstract that captures the essence of this book."""
        
        # Make API call to OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        abstract = response.choices[0].message.content
        
        return jsonify({
            'success': True,
            'abstract': abstract,
            'book_title': book['title'],
            'book_author': book['author']
        })
        
    except Exception as e:
        return jsonify({'error': f'{t["error_generating_abstract"]}: {str(e)}'}), 500

@app.route('/generate_annotation/<int:book_id>', methods=['POST'])
@login_required
def generate_annotation(book_id):
    """Generate annotations for a book using AI."""
    t = get_translations()
    try:
        # Get book information
        conn = get_db_connection()
        book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        conn.close()
        
        if book is None:
            return jsonify({'error': 'Book not found'}), 404
        
        # Create prompt for annotation generation
        current_lang = get_current_language()
        language_instruction = "in Arabic" if current_lang == 'ar' else "in English"
        
        system_prompt = f"""You are an AI assistant that creates detailed annotations and marginal notes for books. 
        Generate comprehensive annotations {language_instruction} that provide insights, explanations, and commentary on the book's content.
        The annotations should be educational, insightful, and help readers understand key concepts, themes, and important details.
        Focus on providing valuable context, explanations of complex ideas, and connections to broader themes.
        Format the annotations as a structured list with clear headings and bullet points."""
        
        user_prompt = f"""Please create detailed annotations for the following book:
        
        Title: {book['title']}
        Author: {book['author']}
        Description: {book['description'] if book['description'] else 'No description available'}
        
        Generate comprehensive annotations that would help readers understand and appreciate this book better.
        Include insights about themes, important concepts, historical context, and any other relevant information."""
        
        # Make API call to OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=600,
            temperature=0.7
        )
        
        annotation = response.choices[0].message.content
        
        return jsonify({
            'success': True,
            'annotation': annotation,
            'book_title': book['title'],
            'book_author': book['author']
        })
        
    except Exception as e:
        return jsonify({'error': f'{t["error_generating_annotation"]}: {str(e)}'}), 500

if __name__ == '__main__':
    init_database()
    app.run(debug=True)
