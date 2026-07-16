from enum import Enum

class Department(str, Enum):
    SALES_MARKETING = "Sales/Marketing"
    TECHNICAL_RD = "Technical/R&D"
    HR_ADMIN = "Human Resources/Admin"
    ACCOUNTS_AUDIT = "Accounts/Audit"
    IT_SYSTEMS = "IT/Systems"


class EmployeeRole(str, Enum):
    EMPLOYEE = "employee"
    DEPT_ADMIN = "dept_admin"
    SUPER_ADMIN = "super_admin"


class BlogStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


class BlogVisibility(str, Enum):
    COMPANY_WIDE = "company_wide"
    DEPARTMENT_ONLY = "department_only"


class AttachmentFileType(str, Enum):
    PDF = "pdf"
    PPTX = "pptx"
    DOCX = "docx"
    XLSX = "xlsx"
    CSV = "csv"
    IMAGE = "image"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class ChunkSourceType(str, Enum):
    BLOG_BODY = "blog_body"
    ATTACHMENT_TEXT = "attachment_text"
    IMAGE_OCR = "image_ocr"
    IMAGE_CAPTION = "image_caption"
    SPREADSHEET_SUMMARY = "spreadsheet_summary"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"