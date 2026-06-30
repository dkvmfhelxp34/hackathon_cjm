#%%
import streamlit as st
import requests
from PIL import Image
import io

# FastAPI 서버 URL 설정
FASTAPI_URL = "http://localhost:8002"

# 페이지 설정
st.set_page_config(
    page_title="PDF & OCR 웹앱",
    layout="wide"
)

# 제목
st.title("📄 PDF 파싱 & 이미지 OCR 웹앱")
st.markdown("---")

# ==================== PDF 파싱 섹션 ====================
st.header("1️⃣ PDF 파싱 (PyPDF2)")

# 1:2 비율로 컬럼 생성
pdf_col1, pdf_col2 = st.columns([1, 2])

with pdf_col1:
    st.subheader("📤 PDF 파일 업로드")
    
    # PDF 파일 업로더
    pdf_file = st.file_uploader(
        "PDF 파일을 선택하세요",
        type=['pdf'],
        key="pdf_uploader"
    )
    
    if pdf_file is not None:
        st.success(f"✅ 파일 선택됨: {pdf_file.name}")
        st.info(f"파일 크기: {pdf_file.size / 1024:.2f} KB")
        
        # 파싱 버튼
        if st.button("📋 PDF 파싱 시작", key="parse_pdf_btn", use_container_width=True):
            
            with st.spinner("PDF 파싱 중..."):
                # FastAPI로 파일 전송
                files = {
                    "file": (pdf_file.name, pdf_file.getvalue(), "application/pdf")
                }
                
                ### 필수과제 1-(1): streamlit -> fastapi로 사용자가 업로드한 pdf 파일 파싱 요청
                respones = requests.post(f"{FASTAPI_URL}/parse-pdf", files=files)
                print(respones)
                if respones.status_code == 200:
                    result = respones.json()
                    st.session_state.pdf_result = result

                    st.success("PDF Parsing sucess")
                else:
                    st.error(f"오류 발생: {respones.json().get('detail', '알수없는 오류')}")

               
with pdf_col2:
    st.subheader("📝 추출된 텍스트")
    
    # 세션 스테이트에 저장된 결과 표시
    if 'pdf_result' in st.session_state:
        result = st.session_state.pdf_result
        
        # 정보 표시
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("총 페이지 수", result['total_pages'])
        with col_b:
            st.metric("추출된 문자 수", result['text_length'])
        with col_c:
            st.metric("파일명", result['filename'][:20] + "..." if len(result['filename']) > 20 else result['filename'])
        
        st.markdown("---")
        
        # 탭으로 전체 텍스트와 페이지별 보기 구분
        tab1, tab2 = st.tabs(["📄 전체 텍스트", "📑 페이지별 보기"])
        
        with tab1:
            # 전체 텍스트 표시
            st.text_area(
                "추출된 전체 텍스트",
                value=result['extracted_text'],
                height=400,
                key="pdf_full_text"
            )
        
        with tab2:
            ########################################
            ### 필수과제 1-(3): 페이지별 텍스트 표시
            for page_info in result['pages']:
                with st.expander(f"페이지 {page_info['page_number']}", expanded=(page_info['page_number'] == 1)):
                    st.text_area(
                        f"Page {page_info['page_number']} 내용",
                        value=page_info['text'],
                        height=200,
                        key=f"pdf_page_{page_info['page_number']}"
                    )
    
            ########################################
    else:
        st.info("👈 왼쪽에서 PDF 파일을 업로드하고 파싱을 시작하세요.")

st.markdown("---")
st.markdown("")

# ==================== 이미지 OCR 섹션 ====================
st.header("2️⃣ 이미지 OCR (EasyOCR)")

# 1:2 비율로 컬럼 생성
ocr_col1, ocr_col2 = st.columns([1, 2])

with ocr_col1:
    st.subheader("📤 이미지 파일 업로드")
    
    # 이미지 파일 업로더
    image_file = st.file_uploader(
        "이미지 파일을 선택하세요",
        type=['jpg', 'jpeg', 'png', 'bmp', 'gif', 'webp'],
        key="image_uploader"
    )
    
    if image_file is not None:
        # 이미지 미리보기
        image = Image.open(image_file)
        st.image(image, caption=f"업로드된 이미지: {image_file.name}", use_container_width=True)
        
        st.success(f"✅ 파일 선택됨: {image_file.name}")
        st.info(f"파일 크기: {image_file.size / 1024:.2f} KB")
        
        # OCR 버튼
        if st.button("🔍 이미지 OCR 시작", key="ocr_image_btn", use_container_width=True):
            with st.spinner("이미지 OCR 처리 중... (처음 실행 시 모델 다운로드로 시간이 걸릴 수 있습니다)"):
                # 파일 포인터를 처음으로 되돌리기
                image_file.seek(0)
                
                # FastAPI로 파일 전송
                files = {
                    "file": (image_file.name, image_file.getvalue(), f"image/{image_file.type}")
                }
                ########################################
                ### 필수과제 2-(1): streamlit -> fastapi로 사용자가 업로드한 이미지 파일 파싱 요청
                response = requests.post(f"{FASTAPI_URL}/ocr-image", files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    # 세션 스테이트에 저장
                    st.session_state.ocr_result = result
                    st.success("✅ OCR 처리 완료!")
                else:
                    st.error(f"❌ 오류 발생: {response.json().get('detail', '알 수 없는 오류')}")
                ########################################

with ocr_col2:
    st.subheader("📝 추출된 텍스트")
    
    # 세션 스테이트에 저장된 결과 표시
    if 'ocr_result' in st.session_state:
        result = st.session_state.ocr_result
        
        # 정보 표시
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("감지된 텍스트 수", result['total_detections'])
        with col_b:
            st.metric("파일명", result['filename'][:30] + "..." if len(result['filename']) > 30 else result['filename'])
        
        # 추출된 전체 텍스트 표시
        st.text_area(
            "추출된 전체 텍스트",
            value=result['extracted_text'],
            height=400,
            key="ocr_full_text"
        )
    else:
        st.info("👈 왼쪽에서 이미지 파일을 업로드하고 OCR을 시작하세요.")

