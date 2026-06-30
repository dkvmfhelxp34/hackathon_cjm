#%%
from typing import Any


from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import PyPDF2
import easyocr
import io
import numpy as np
from PIL import Image
import uvicorn

#%%
app = FastAPI(title="PDF & OCR API")

# CORS 설정 (Streamlit과 통신을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# EasyOCR reader 초기화 (한국어, 영어)
reader = easyocr.Reader(['ko', 'en'], gpu=True)


@app.get("/")
async def root():
    return {"message": "PDF & OCR API is running"}


@app.post("/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    """
    PDF 파일을 업로드받아 PyPDF2로 텍스트를 추출합니다.
    """
    try:
        # 파일 확장자 검증
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")
        
        # PDF 파일 읽기
        contents = await file.read()
        pdf_file = io.BytesIO(contents)
        
        # PyPDF2로 텍스트 추출
        ########################################
        ### 필수과제 1-(2): PyPDF2로 텍스트 추출
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        total_pages = len(pdf_reader.pages) 

        ########################################
        
        extracted_text = ""
        page_texts = []
        
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            page_texts.append({
                "page_number": page_num + 1,
                "text": page_text
            })
            extracted_text += f"\n--- 페이지 {page_num + 1} ---\n"
            extracted_text += page_text
        
        return {
            "success": True,
            "filename": file.filename,
            "total_pages": total_pages,
            "extracted_text": extracted_text,
            "pages": page_texts,
            "text_length": len(extracted_text)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 파싱 중 오류 발생: {str(e)}")


@app.post("/ocr-image")
async def ocr_image(file: UploadFile = File(...)):
    """
    이미지 파일을 업로드받아 EasyOCR로 텍스트를 추출합니다.
    """
    try:
        # 파일 확장자 검증
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            raise HTTPException(
                status_code=400, 
                detail="이미지 파일만 업로드 가능합니다. (jpg, jpeg, png, bmp, gif, webp)"
            )
        
        # 이미지 파일 읽기
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # numpy array로 변환
        img_array = np.array(image)
        
        ########################################
        ### 필수과제 2-(2): EasyOCR로 텍스트 추출
        result_detailed = reader.readtext(img_array)
        
        # 텍스트만 추출
        result_simple = reader.readtext(img_array, detail=0)
        
        # 결과 정리
        extracted_data = []
        for detection in result_detailed:
            bbox, text, confidence = detection
            extracted_data.append({
                "text": text,
                "confidence": float(confidence)
            })
        ########################################
        
        # 모든 텍스트를 하나로 합치기
        full_text = " ".join(result_simple)
        
        return {
            "success": True,
            "filename": file.filename,
            "extracted_text": full_text,
            "detailed_results": extracted_data,
            "total_detections": len(extracted_data)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 처리 중 오류 발생: {str(e)}")

#%%
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)


# %%
