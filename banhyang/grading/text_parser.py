import io
from pypdf import PdfReader
from docx import Document

class DocumentParser:
    """
    바이너리 데이터를 받아 순수 텍스트로 추출하는 파서 클래스
    """
    
    @staticmethod
    def extract_text(file_bytes: bytes, mime_type: str) -> str:
        """
        파일의 MimeType을 확인하여 적절한 파싱 메서드를 호출합니다.
        """
        if 'application/pdf' in mime_type:
            return DocumentParser._parse_pdf(file_bytes)
        elif 'wordprocessingml.document' in mime_type:
            return DocumentParser._parse_docx(file_bytes)
        else:
            raise ValueError(f"지원하지 않는 파일 형식입니다. (현재 MimeType: {mime_type})")

    @staticmethod
    def _parse_pdf(file_bytes: bytes) -> str:
        """PDF 바이너리에서 텍스트 추출"""
        try:
            # 바이너리 데이터를 메모리 상의 파일처럼 취급 (io.BytesIO)
            reader = PdfReader(io.BytesIO(file_bytes))
            text_pages = []
            
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_pages.append(extracted)
                    
            # 추출된 모든 페이지의 텍스트를 줄바꿈으로 연결하여 반환
            return '\n'.join(text_pages)
            
        except Exception as e:
            print(f"PDF 파싱 중 에러 발생: {e}")
            return ""

    @staticmethod
    def _parse_docx(file_bytes: bytes) -> str:
        """DOCX 바이너리에서 텍스트 추출"""
        try:
            doc = Document(io.BytesIO(file_bytes))
            text_paragraphs = []
            
            for paragraph in doc.paragraphs:
                # 빈 줄이 아닌 문단만 추가
                if paragraph.text.strip():
                    text_paragraphs.append(paragraph.text)
                    
            return '\n'.join(text_paragraphs)
            
        except Exception as e:
            print(f"DOCX 파싱 중 에러 발생: {e}")
            return ""