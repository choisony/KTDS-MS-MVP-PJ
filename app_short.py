import os
import streamlit as st
import zipfile
import io
import json
from datetime import datetime
from openai import AzureOpenAI

# 환경 변수 및 클라이언트 설정
client = AzureOpenAI(
    api_version=os.getenv("OPENAI_API_VERSION", "2024-12-01-preview"),
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
    api_key=os.getenv("OPENAI_API_KEY"),
)
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")

# 페이지 설정
st.set_page_config(page_title="C# to Java 코드변환 AI Agent", layout="wide")

# CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #6b7280, #9ca3af);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .analysis-box {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
    }
    .analysis-box h5 {
        margin: 0 0 0.5rem 0;
        font-size: 0.9rem;
        color: #495057;
    }
    .analysis-box p, .analysis-box div {
        font-size: 0.85rem;
        line-height: 1.4;
        margin: 0.2rem 0;
    }
</style>
""", unsafe_allow_html=True)

def test_connection():
    """Azure OpenAI 연결 테스트"""
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=50,
            temperature=0.1,
        )
        return True, "연결 성공!"
    except Exception as e:
        return False, str(e)

def convert_csharp_to_java(csharp_code):
    """C# 코드를 Java로 변환"""
    prompt = f"""C# 코드를 Java로 변환해주세요:

```csharp
{csharp_code}
```

JSON 형식으로 응답:
{{
    "java_code": "변환된 Java 코드",
    "notes": "주요 변환 사항",
    "warnings": ["주의사항들"]
}}"""
    
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "C# to Java 변환 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.1,
        )
        
        result_text = response.choices[0].message.content
        
        if "```json" in result_text:
            json_start = result_text.find("```json") + 7
            json_end = result_text.find("```", json_start)
            json_text = result_text[json_start:json_end].strip()
        else:
            json_text = result_text
            
        return json.loads(json_text)
        
    except Exception as e:
        return {
            "java_code": f"// 변환 오류: {str(e)}",
            "notes": f"오류 발생: {str(e)}",
            "warnings": ["변환 실패"]
        }

def analyze_csharp_code(csharp_code):
    """C# 코드 분석"""
    prompt = f"""C# 코드를 분석해주세요:

```csharp
{csharp_code}
```

JSON 형식으로 응답:
{{
    "issues": [
        {{
            "type": "성능|보안|가독성|유지보수",
            "description": "문제점 설명"
        }}
    ],
    "suggestions": [
        {{
            "category": "리팩토링|성능|구조|네이밍",
            "suggestion": "개선 방안"
        }}
    ],
    "java_conversion_notes": [
        "Java 변환시 주의사항1",
        "Java 변환시 주의사항2"
    ],
    "summary": "전반적인 코드 평가"
}}"""
    
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "C# 코드 분석 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.1,
        )
        
        result_text = response.choices[0].message.content
        
        if "```json" in result_text:
            json_start = result_text.find("```json") + 7
            json_end = result_text.find("```", json_start)
            json_text = result_text[json_start:json_end].strip()
        else:
            json_text = result_text
            
        return json.loads(json_text)
        
    except Exception as e:
        return {
            "issues": [],
            "suggestions": [],
            "java_conversion_notes": [],
            "summary": f"분석 오류: {str(e)}"
        }

def extract_cs_files(uploaded_files):
    """업로드된 파일에서 C# 코드 추출"""
    files = []
    for file in uploaded_files:
        try:
            if file.name.endswith(".cs"):
                content = file.read().decode("utf-8")
                files.append({"filename": file.name, "content": content})
            elif file.name.endswith(".zip"):
                with zipfile.ZipFile(file, "r") as zip_ref:
                    for info in zip_ref.filelist:
                        if info.filename.endswith(".cs") and not info.is_dir():
                            with zip_ref.open(info) as cs_file:
                                content = cs_file.read().decode("utf-8")
                                files.append({"filename": info.filename, "content": content})
        except Exception as e:
            st.error(f"파일 처리 오류 ({file.name}): {str(e)}")
    return files

def create_zip(results):
    """변환 결과를 ZIP으로 생성"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for result in results:
            java_filename = result["filename"].replace(".cs", ".java")
            zip_file.writestr(java_filename, result["java_code"])
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def main():
    # 헤더
    st.markdown("""
    <div class="main-header">
        <h1>C# to Java 코드변환 AI Agent</h1>
    </div>
    """, unsafe_allow_html=True)

    # 사이드바
    with st.sidebar:
        st.markdown("### 연결 상태")
        if st.button("테스트"):
            success, msg = test_connection()
            if success:
                st.success(msg)
            else:
                st.error(msg)
        
        st.markdown("### 사용법")
        st.info("1. C# 파일 업로드 또는 코드 입력\n2. 변환 버튼 클릭\n3. 결과 확인 및 다운로드")

    # 탭
    tab1, tab2, tab3, tab4 = st.tabs(["파일 변환", "변환 결과", "코드 변환", "코드 분석"])

    # 파일 변환 탭
    with tab1:
        st.markdown("### 파일 업로드 변환")
        
        uploaded_files = st.file_uploader("C# 파일 선택", type=["cs", "zip"], accept_multiple_files=True)
        
        if uploaded_files and st.button("변환 시작", type="primary"):
            # 파일 추출
            with st.spinner("파일에서 C# 코드 추출 중..."):
                cs_files = extract_cs_files(uploaded_files)
                
                if not cs_files:
                    st.error("C# 파일을 찾을 수 없습니다.")
                    return
            
            st.success(f"{len(cs_files)}개의 C# 파일이 추출되었습니다.")
            
            # 진행률 표시를 위한 컨테이너
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            
            # 각 파일 변환
            for i, file_info in enumerate(cs_files):
                # 진행률 업데이트
                progress = (i + 1) / len(cs_files)
                progress_bar.progress(progress)
                status_text.text(f"변환 중: {file_info['filename']} ({i+1}/{len(cs_files)})")
                
                # 변환 실행
                result = convert_csharp_to_java(file_info["content"])
                result.update({"filename": file_info["filename"], "original_content": file_info["content"]})
                results.append(result)
            
            # 완료 표시
            progress_bar.progress(1.0)
            status_text.text("변환 완료!")
            st.session_state.file_results = results
            st.success(f"{len(results)}개 파일 변환 완료!")

    # 변환 결과 탭
    with tab2:
        st.markdown("### 변환 결과")
        
        if "file_results" in st.session_state:
            results = st.session_state.file_results
            
            # 통계
            col1, col2 = st.columns(2)
            with col1:
                st.metric("변환된 파일", len(results))
            with col2:
                success_count = len([r for r in results if "오류" not in r["java_code"]])
                st.metric("성공률", f"{(success_count/len(results)*100):.1f}%")
            
            # 개별 결과
            for i, result in enumerate(results):
                java_filename = result["filename"].replace(".cs", ".java")
                with st.expander(f"{result['filename']} → {java_filename}"):
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**원본 C# 코드**")
                        st.code(result.get("original_content", ""), language="csharp")
                    
                    with col2:
                        st.markdown("**변환된 Java 코드**")
                        st.code(result["java_code"], language="java")
                    
                    if result.get("notes"):
                        st.info(f"변환 노트: {result['notes']}")
                    
                    if result.get("warnings"):
                        st.markdown("**주의사항:**")
                        for warning in result["warnings"]:
                            st.warning(warning)
                    
                    st.download_button(f"{java_filename} 다운로드", result["java_code"], java_filename, key=f"download_{i}")
            
            # 전체 다운로드
            zip_data = create_zip(results)
            st.download_button(
                "모든 파일 ZIP 다운로드",
                zip_data,
                f"converted_java_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
                mime="application/zip",
                type="primary"
            )
        else:
            st.info("파일 변환 탭에서 파일을 변환해주세요.")

    # 코드 변환 탭
    with tab3:
        st.markdown("### 코드 직접 변환")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csharp_input = st.text_area(
                "C# 코드 입력:",
                height=400,
                placeholder="""public class Person
{
    public string Name { get; set; }
    public int Age { get; set; }
    
    public void DisplayInfo()
    {
        Console.WriteLine($"Name: {Name}, Age: {Age}");
    }
}"""
            )
            
            if st.button("즉시 변환", type="primary"):
                if csharp_input.strip():
                    with st.spinner("변환 중..."):
                        result = convert_csharp_to_java(csharp_input)
                        st.session_state.instant_result = result
                else:
                    st.warning("C# 코드를 입력하세요.")
        
        with col2:
            st.markdown("**Java 변환 결과**")
            
            if "instant_result" in st.session_state:
                result = st.session_state.instant_result
                st.code(result["java_code"], language="java")
                
                if result.get("notes"):
                    st.info(f"변환 노트: {result['notes']}")
                
                if result.get("warnings"):
                    for warning in result["warnings"]:
                        st.warning(warning)
                
                st.download_button("Java 파일 다운로드", result["java_code"], "ConvertedCode.java", mime="text/plain")
            else:
                st.info("왼쪽에 C# 코드를 입력하고 변환 버튼을 클릭하세요.")

    # 코드 분석 탭
    with tab4:
        st.markdown("### C# 코드 분석")
        
        col1, col2 = st.columns(2)
        
        with col1:
            analysis_input = st.text_area(
                "분석할 C# 코드 입력:",
                height=350,
                placeholder="""public class OrderService
{
    private List<Order> orders = new List<Order>();
    
    public void ProcessOrder(Order order)
    {
        if (order != null && order.Items.Count > 0)
        {
            foreach (var item in order.Items)
            {
                ProcessItem(item);
            }
        }
    }
}"""
            )
            
            if st.button("코드 분석", type="primary"):
                if analysis_input.strip():
                    with st.spinner("분석 중..."):
                        analysis = analyze_csharp_code(analysis_input)
                        st.session_state.analysis_result = analysis
                else:
                    st.warning("분석할 C# 코드를 입력하세요.")
        
        with col2:
            st.markdown("### 분석 결과")
            
            if "analysis_result" in st.session_state:
                result = st.session_state.analysis_result
                
                if result.get("summary"):
                    st.markdown(f"""
                    <div class="analysis-box">
                        <h5>요약</h5>
                        <p>{result['summary']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                if result.get("issues"):
                    issues_html = ""
                    for i, issue in enumerate(result["issues"], 1):
                        issues_html += f"<p>{i}. <strong>{issue.get('type', 'Unknown')}</strong>: {issue.get('description', '')}</p>"
                    
                    st.markdown(f"""
                    <div class="analysis-box">
                        <h5>발견된 문제점</h5>
                        {issues_html}
                    </div>
                    """, unsafe_allow_html=True)
                
                if result.get("suggestions"):
                    suggestions_html = ""
                    for i, suggestion in enumerate(result["suggestions"], 1):
                        suggestions_html += f"<p>{i}. <strong>{suggestion.get('category', 'General')}</strong>: {suggestion.get('suggestion', '')}</p>"
                    
                    st.markdown(f"""
                    <div class="analysis-box">
                        <h5>개선 제안</h5>
                        {suggestions_html}
                    </div>
                    """, unsafe_allow_html=True)
                
                if result.get("java_conversion_notes"):
                    notes_html = ""
                    for i, note in enumerate(result["java_conversion_notes"], 1):
                        notes_html += f"<p>{i}. {note}</p>"
                    
                    st.markdown(f"""
                    <div class="analysis-box">
                        <h5>Java 변환시 유의사항</h5>
                        {notes_html}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("왼쪽에 C# 코드를 입력하고 분석 버튼을 클릭하세요.")

    # 푸터
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #666;'>C# to Java 코드변환 AI Agent by AI</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()