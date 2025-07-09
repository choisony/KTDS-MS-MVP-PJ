import os
from dotenv import load_dotenv
import streamlit as st
import zipfile
import io
import json
from datetime import datetime
from openai import AzureOpenAI

# 환경 변수 로드
load_dotenv()

# 설정
CONFIG = {
    "endpoint": os.getenv("AZURE_ENDPOINT"),
    "model_name": "gpt-4.1",
    "deployment_name": os.getenv("DEPLOYMENT_NAME"),
    "api_key": os.getenv("OPENAI_API_KEY"),
    "api_version": os.getenv("OPENAI_API_VERSION", "2024-12-01-preview"),
}

# Azure OpenAI 클라이언트 설정
client = AzureOpenAI(
    api_version=CONFIG["api_version"],
    azure_endpoint=CONFIG["endpoint"],
    api_key=CONFIG["api_key"],
)

# 페이지 설정
st.set_page_config(page_title="C# to Java 코드 전환 Agent", layout="wide")


# CSS 스타일링
def apply_styles():
    st.markdown(
        """
    <style>
        .main-header {
            background: linear-gradient(135deg, #6b7280 0%, #9ca3af 50%, #d1d5db 100%);
            padding: 1rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 1rem;
        }
        .analysis-card {
            background: #f8f9fa; padding: 1rem; border-radius: 8px;
            border-left: 4px solid #007bff; margin: 0.5rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .analysis-card h5 { margin: 0 0 0.5rem 0; font-size: 1rem; }
        .analysis-card p { margin: 0.3rem 0; line-height: 1.4; }
        .issue-high { background: #f8d7da; border-left: 4px solid #dc3545; padding: 0.8rem; margin: 0.3rem 0; border-radius: 6px; }
        .issue-medium { background: #fff3cd; border-left: 4px solid #ffc107; padding: 0.8rem; margin: 0.3rem 0; border-radius: 6px; }
        .issue-low { background: #d1ecf1; border-left: 4px solid #17a2b8; padding: 0.8rem; margin: 0.3rem 0; border-radius: 6px; }
        .option-info { background: #e7f3ff; padding: 0.5rem; border-radius: 4px; margin: 0.5rem 0; border-left: 3px solid #007bff; }
    </style>
    """,
        unsafe_allow_html=True,
    )


# Azure OpenAI 연결 테스트
def test_connection():
    try:
        response = client.chat.completions.create(
            model=CONFIG["deployment_name"],
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": "Hello! Please respond with 'Connection successful!'",
                },
            ],
            max_tokens=50,
            temperature=0.1,
        )
        return True, response.choices[0].message.content
    except Exception as e:
        return False, str(e)


# AI 호출 공통 함수
def call_ai(system_prompt, user_prompt, max_tokens=4000):
    try:
        response = client.chat.completions.create(
            model=CONFIG["deployment_name"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.1,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"AI 호출 오류: {e}")
        return None


# JSON 파싱 유틸리티
def parse_json_response(response_text, default_response):
    try:
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        else:
            json_text = response_text
        return json.loads(json_text)
    except json.JSONDecodeError:
        return default_response


# 변환 옵션을 시스템 프롬프트에 포함하는 함수
def create_conversion_system_prompt(include_comments=True, generate_getters_setters=True, use_java_conventions=True):
    base_prompt = "당신은 C# to Java 코드 변환 전문가입니다."
    
    options = []
    if include_comments:
        options.append("- 원본 C# 코드의 주석을 Java 스타일로 변환하여 포함하세요")
    else:
        options.append("- 주석은 제거하고 코드만 변환하세요")
    
    if generate_getters_setters:
        options.append("- C# Properties는 private 필드와 public getter/setter 메서드로 변환하세요")
    else:
        options.append("- C# Properties는 public 필드로 간단히 변환하세요")
    
    if use_java_conventions:
        options.append("- Java 네이밍 컨벤션을 적용하세요 (camelCase, 패키지명 소문자 등)")
    else:
        options.append("- 원본 C# 네이밍을 최대한 유지하세요")
    
    if options:
        base_prompt += "\n\n변환 옵션:\n" + "\n".join(options)
    
    return base_prompt


# C# 코드 분석
def analyze_csharp_code(csharp_code, filename=""):
    system_prompt = "당신은 20년 경력의 시니어 C# 개발자이자 코드 리뷰 전문가입니다. 정확하고 실용적인 분석을 제공해주세요."

    user_prompt = f"""
다음 C# 코드를 분석해주세요.

파일명: {filename}
C# 코드:
```csharp
{csharp_code}
```

다음 JSON 형식으로 응답해주세요:
{{
    "complexity_score": 숫자(1-10),
    "quality_score": 숫자(1-100),
    "code_patterns": ["패턴1", "패턴2"],
    "potential_issues": [
        {{"type": "성능|보안|가독성|유지보수", "description": "문제점 설명", "severity": "low|medium|high", "line_info": "해당 라인 정보"}}
    ],
    "refactoring_suggestions": [
        {{"category": "성능|구조|네이밍|보안", "suggestion": "구체적인 개선 방안", "benefit": "개선시 얻을 수 있는 효과", "priority": "low|medium|high"}}
    ],
    "java_conversion_notes": ["Java 변환시 주의사항1", "Java 변환시 주의사항2"],
    "code_metrics": {{"lines_of_code": 숫자, "methods_count": 숫자, "classes_count": 숫자, "estimated_maintainability": "low|medium|high"}},
    "summary": "코드에 대한 전반적인 평가와 요약"
}}
"""

    response_text = call_ai(system_prompt, user_prompt)
    if not response_text:
        return None

    default_response = {
        "complexity_score": 5,
        "quality_score": 70,
        "code_patterns": [],
        "potential_issues": [],
        "refactoring_suggestions": [],
        "java_conversion_notes": [],
        "code_metrics": {},
        "summary": "분석 중 오류가 발생했습니다.",
    }

    result = parse_json_response(response_text, default_response)

    # 분석 히스토리 저장
    if "analysis_history" not in st.session_state:
        st.session_state.analysis_history = []

    analysis_record = {
        **result,
        "filename": filename,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "code_length": len(csharp_code),
    }
    st.session_state.analysis_history.append(analysis_record)
    st.session_state.analysis_history = st.session_state.analysis_history[
        -10:
    ]  # 최근 10개만 유지

    return result


# C# to Java 변환 (옵션 적용)
def convert_csharp_to_java(csharp_code, filename="", include_comments=True, generate_getters_setters=True, use_java_conventions=True):
    system_prompt = create_conversion_system_prompt(include_comments, generate_getters_setters, use_java_conventions)

    user_prompt = f"""
다음 C# 코드를 Java로 변환해주세요.

파일명: {filename}
C# 코드:
```csharp
{csharp_code}
```

JSON 형식으로 응답해주세요:
{{
    "java_code": "변환된 Java 코드",
    "imports": ["필요한 import 문들"],
    "conversion_notes": "주요 변환 사항 설명",
    "warnings": ["주의가 필요한 부분들"],
    "applied_options": {{"include_comments": {include_comments}, "generate_getters_setters": {generate_getters_setters}, "use_java_conventions": {use_java_conventions}}}
}}
"""

    response_text = call_ai(system_prompt, user_prompt)
    if not response_text:
        return {
            "java_code": f"// 변환 오류 발생",
            "imports": [],
            "conversion_notes": "변환 실패",
            "warnings": ["변환 실패"],
            "applied_options": {"include_comments": include_comments, "generate_getters_setters": generate_getters_setters, "use_java_conventions": use_java_conventions}
        }

    default_response = {
        "java_code": response_text,
        "imports": [],
        "conversion_notes": "AI가 생성한 변환 결과입니다.",
        "warnings": ["JSON 파싱 실패로 인해 상세 정보가 제한됩니다."],
        "applied_options": {"include_comments": include_comments, "generate_getters_setters": generate_getters_setters, "use_java_conventions": use_java_conventions}
    }

    return parse_json_response(response_text, default_response)


# 파일에서 C# 코드 추출 및 전체 프로젝트 구조 보존
def extract_csharp_files(uploaded_files):
    extracted_files = []
    project_structure = {}  # 전체 프로젝트 구조 저장

    for uploaded_file in uploaded_files:
        try:
            if uploaded_file.name.endswith(".cs"):
                content = uploaded_file.read().decode("utf-8")
                extracted_files.append(
                    {"filename": uploaded_file.name, "content": content}
                )
            elif uploaded_file.name.endswith(".zip"):
                # ZIP 파일의 전체 구조를 메모리에 저장
                with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
                    project_structure[uploaded_file.name] = {}

                    for file_info in zip_ref.filelist:
                        if not file_info.is_dir():
                            try:
                                file_content = zip_ref.read(file_info)

                                # CS 파일인 경우 텍스트로 디코딩하여 변환 대상에 추가
                                if file_info.filename.endswith(".cs"):
                                    try:
                                        content = file_content.decode("utf-8")
                                        extracted_files.append(
                                            {
                                                "filename": file_info.filename,
                                                "content": content,
                                                "zip_source": uploaded_file.name,
                                            }
                                        )
                                    except UnicodeDecodeError:
                                        st.warning(
                                            f"파일 인코딩 오류: {file_info.filename}"
                                        )

                                # 모든 파일을 프로젝트 구조에 저장 (바이너리 형태로)
                                project_structure[uploaded_file.name][
                                    file_info.filename
                                ] = {
                                    "content": file_content,
                                    "is_text": file_info.filename.endswith(
                                        (
                                            ".cs",
                                            ".txt",
                                            ".md",
                                            ".json",
                                            ".xml",
                                            ".config",
                                            ".yml",
                                            ".yaml",
                                        )
                                    ),
                                    "file_info": file_info,
                                }

                            except Exception as e:
                                st.warning(
                                    f"파일 읽기 오류 ({file_info.filename}): {str(e)}"
                                )
        except Exception as e:
            st.error(f"파일 처리 오류 ({uploaded_file.name}): {str(e)}")

    # 세션 상태에 프로젝트 구조 저장
    st.session_state.project_structure = project_structure
    return extracted_files


# 프로젝트 단위의 코드 변환
def analyze_project_context(extracted_files):
    """프로젝트 전체 컨텍스트 분석"""
    if len(extracted_files) <= 1:
        return ""
    
    system_prompt = """
    다음 C# 프로젝트를 분석하여 Java 변환에 필요한 정보를 JSON으로 제공해주세요:
    
    {
        "namespaces": ["네임스페이스 목록"],
        "interfaces": [{"name": "인터페이스명", "methods": ["메서드들"]}],
        "base_classes": [{"name": "클래스명", "properties": ["속성들"]}],
        "custom_types": ["커스텀 타입들"],
        "dependencies": [{"from": "클래스A", "to": "클래스B", "type": "상속|구현|의존"}]
    }
    """
    
    # 파일 요약 (토큰 제한 고려)
    file_summaries = []
    for file_info in extracted_files[:10]:  # 최대 10개 파일만
        summary = f"// {file_info['filename']}\n"
        lines = file_info['content'].split('\n')
        
        # 클래스/인터페이스 선언부만 추출
        for line in lines:
            if any(keyword in line for keyword in ['class ', 'interface ', 'public ', 'private ', 'protected ']):
                summary += line.strip() + '\n'
        
        file_summaries.append(summary)
    
    project_summary = '\n\n'.join(file_summaries)
    
    try:
        response = call_ai(system_prompt, project_summary, max_tokens=3000)
        return parse_json_response(response, {"namespaces": [], "interfaces": [], "base_classes": [], "custom_types": [], "dependencies": []})
    except:
        return ""

def convert_csharp_to_java_with_context(csharp_code, filename="", project_context="", include_comments=True, generate_getters_setters=True, use_java_conventions=True):
    """프로젝트 컨텍스트를 고려한 C# to Java 변환"""
    
    context_info = ""
    if project_context:
        context_info = f"""
프로젝트 컨텍스트 정보:
{json.dumps(project_context, ensure_ascii=False, indent=2)}

이 정보를 활용하여 타입 변환 시 일관성을 유지해주세요.
"""
    
    system_prompt = create_conversion_system_prompt(include_comments, generate_getters_setters, use_java_conventions)
    system_prompt += f"""

{context_info}

다음 규칙을 준수해주세요:
1. 클래스명은 일관되게 변환
2. 인터페이스 구현 관계 유지
3. 커스텀 타입은 적절한 Java 타입으로 매핑
4. 네임스페이스는 package로 변환
"""

    user_prompt = f"""
다음 C# 코드를 Java로 변환해주세요.

파일명: {filename}
C# 코드:
```csharp
{csharp_code}
```

JSON 형식으로 응답해주세요:
{{
    "java_code": "변환된 Java 코드",
    "package_declaration": "package 선언",
    "imports": ["필요한 import 문들"],
    "conversion_notes": "주요 변환 사항 설명",
    "warnings": ["주의가 필요한 부분들"],
    "type_mappings": {{"C#타입": "Java타입"}},
    "applied_options": {{"include_comments": {include_comments}, "generate_getters_setters": {generate_getters_setters}, "use_java_conventions": {use_java_conventions}}}
}}
"""

    response_text = call_ai(system_prompt, user_prompt, max_tokens=5000)
    if not response_text:
        return {
            "java_code": f"// 변환 오류 발생",
            "package_declaration": "",
            "imports": [],
            "conversion_notes": "변환 실패",
            "warnings": ["변환 실패"],
            "type_mappings": {},
            "applied_options": {"include_comments": include_comments, "generate_getters_setters": generate_getters_setters, "use_java_conventions": use_java_conventions}
        }

    default_response = {
        "java_code": response_text,
        "package_declaration": "",
        "imports": [],
        "conversion_notes": "AI가 생성한 변환 결과입니다.",
        "warnings": ["JSON 파싱 실패로 인해 상세 정보가 제한됩니다."],
        "type_mappings": {},
        "applied_options": {"include_comments": include_comments, "generate_getters_setters": generate_getters_setters, "use_java_conventions": use_java_conventions}
    }

    return parse_json_response(response_text, default_response)


# 전체 프로젝트 ZIP 파일 생성 (CS 파일을 Java로 변환하고 나머지 파일 유지)
def create_complete_project_zip(conversion_results):
    """변환 결과와 원본 프로젝트 구조를 결합하여 완전한 프로젝트 ZIP 생성"""
    zip_buffer = io.BytesIO()

    # 변환된 Java 파일들의 매핑 생성
    java_files = {}
    for result in conversion_results:
        original_path = result["original_filename"]
        java_path = original_path.replace(".cs", ".java")
        java_files[original_path] = {
            "java_path": java_path,
            "java_content": result["java_code"],
        }

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 프로젝트 구조가 있는 경우 (ZIP 파일에서 추출된 경우)
        if (
            "project_structure" in st.session_state
            and st.session_state.project_structure
        ):
            original_name = list(st.session_state.project_structure.keys())[0].replace(
                ".zip", ""
            )
            for zip_name, files in st.session_state.project_structure.items():
                for file_path, file_data in files.items():
                    # CS 파일인 경우 Java로 변환된 파일 추가
                    if file_path.endswith(".cs") and file_path in java_files:
                        java_path = java_files[file_path]["java_path"]
                        java_content = java_files[file_path]["java_content"]
                        zip_file.writestr(java_path, java_content.encode("utf-8"))
                    else:
                        # 다른 모든 파일들은 원본 그대로 유지
                        zip_file.writestr(file_path, file_data["content"])
        else:
            # 개별 CS 파일들만 업로드된 경우 (기존 방식)
            for result in conversion_results:
                zip_file.writestr(result["java_filename"], result["java_code"])

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


# Java 파일만 포함된 ZIP 생성
def create_java_only_zip(conversion_results):
    """Java 파일만 포함된 ZIP 파일 생성"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for result in conversion_results:
            zip_file.writestr(result["java_filename"], result["java_code"])
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


# 분석 결과 시각화
def display_analysis_results(analysis_data):
    if not analysis_data:
        st.error("분석 데이터가 없습니다.")
        return

    # 전체 요약
    if analysis_data.get("summary"):
        st.markdown("#### 분석 요약")
        st.markdown(
            f'<div class="analysis-card"><p>{analysis_data["summary"]}</p></div>',
            unsafe_allow_html=True,
        )

    # 리팩토링 제안
    if analysis_data.get("refactoring_suggestions"):
        st.markdown("#### 리팩토링 제안")
        for suggestion in analysis_data["refactoring_suggestions"]:
            priority = suggestion.get("priority", "medium")
            with st.expander(
                f"{suggestion.get('category', 'General')} - {priority.upper()} 우선순위"
            ):
                st.markdown(f"**제안:** {suggestion.get('suggestion', '')}")
                st.markdown(f"**효과:** {suggestion.get('benefit', '')}")

    # 잠재적 문제점
    if analysis_data.get("potential_issues"):
        st.markdown("#### 잠재적 문제점")
        for issue in analysis_data["potential_issues"]:
            severity = issue.get("severity", "medium")
            line_info = (
                f"<p><strong>위치:</strong> {issue.get('line_info', '')}</p>"
                if issue.get("line_info")
                else ""
            )
            st.markdown(
                f"""
            <div class="analysis-card issue-{severity}">
                <h5>{issue.get('type', 'Unknown')} - {severity.upper()}</h5>
                <p><strong>문제:</strong> {issue.get('description', 'No description')}</p>
                {line_info}
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Java 변환 주의사항
    if analysis_data.get("java_conversion_notes"):
        st.markdown("#### Java 변환 시 주의사항")
        for i, note in enumerate(analysis_data["java_conversion_notes"], 1):
            st.info(f"**{i}.** {note}")

    # 코드 패턴
    if analysis_data.get("code_patterns"):
        st.markdown("#### 발견된 코드 패턴")
        pattern_cols = st.columns(min(len(analysis_data["code_patterns"]), 4))
        for i, pattern in enumerate(analysis_data["code_patterns"][:4]):
            with pattern_cols[i % 4]:
                st.markdown(
                    f'<div class="analysis-card"><h5>{pattern}</h5></div>',
                    unsafe_allow_html=True,
                )

    # 코드 메트릭
    if analysis_data.get("code_metrics"):
        st.markdown("#### 코드 메트릭")
        metrics = analysis_data["code_metrics"]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("코드 라인 수", metrics.get("lines_of_code", 0))
        with col2:
            st.metric("메서드 수", metrics.get("methods_count", 0))
        with col3:
            st.metric("클래스 수", metrics.get("classes_count", 0))


# 사이드바 설정
def setup_sidebar():
    with st.sidebar:
        st.markdown("### OpenAI 연결 상태")
        if st.button("테스트", key="sidebar_connection_test"):
            with st.spinner("연결 테스트 중..."):
                success, message = test_connection()
                if success:
                    st.success("연결 성공!")
                    st.info(f"응답: {message}")
                else:
                    st.error("연결 실패")
                    st.error(f"오류: {message}")

        st.markdown("### 사용법")
        st.info(
            """
        1. C# 파일(.cs) 또는 프로젝트(.zip) 업로드
        2. 변환 옵션 설정
        3. 변환 시작 버튼 클릭
        4. 결과 확인 및 다운로드
        5. 코드 분석 탭에서 C#코드 분석
        """
        )

        st.markdown("### 현재 설정")
        st.text(f"모델: {CONFIG['deployment_name']}")
        st.text(f"API 버전: {CONFIG['api_version']}")


# 파일 변환 탭
def file_conversion_tab():
    st.markdown("### C# 파일 업로드 및 변환")

    uploaded_files = st.file_uploader(
        "C# 파일 또는 프로젝트를 선택하세요",
        type=["cs", "zip"],
        accept_multiple_files=True,
        help="개별 .cs 파일 또는 전체 프로젝트 .zip 파일을 업로드할 수 있습니다.",
    )

    # 변환 옵션
    st.markdown("---")
    st.markdown("#### 변환 옵션")
    
    col1, col2 = st.columns(2)
    
    with col1:
        include_comments = st.checkbox("주석 포함", value=True, help="C# 주석을 Java 스타일로 변환하여 포함합니다")
        generate_getters_setters = st.checkbox("Getter/Setter 자동 생성", value=True, help="C# Properties를 private 필드 + getter/setter로 변환합니다")
    
    with col2:
        use_java_conventions = st.checkbox("Java 네이밍 컨벤션 적용", value=True, help="PascalCase → camelCase 등 Java 스타일로 변환합니다")
        use_project_context = st.checkbox("프로젝트 단위로 변환 (다중 파일시 권장)", value=False, help="다중 파일 간의 의존성을 분석하여 더 정확한 변환을 수행합니다")

    if uploaded_files:
        st.success(f"{len(uploaded_files)}개 파일이 업로드되었습니다.")

        if st.button("변환 시작", type="primary"):
            with st.spinner("파일에서 C# 코드 추출 중..."):
                extracted_files = extract_csharp_files(uploaded_files)

            if not extracted_files:
                st.error("C# 파일을 찾을 수 없습니다.")
                return

            st.success(f"{len(extracted_files)}개의 C# 파일이 추출되었습니다.")

            # 프로젝트 컨텍스트 분석 (다중 파일인 경우)
            project_context = ""
            if use_project_context and len(extracted_files) > 1:
                with st.spinner("프로젝트 구조 분석 중..."):
                    project_context = analyze_project_context(extracted_files)
                    if project_context:
                        st.info("프로젝트 분석 완료!")

            conversion_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, file_info in enumerate(extracted_files):
                progress = (i + 1) / len(extracted_files)
                progress_bar.progress(progress)
                status_text.text(
                    f"변환 중: {file_info['filename']} ({i+1}/{len(extracted_files)})"
                )

                # 컨텍스트 정보 포함 변환
                if project_context:
                    result = convert_csharp_to_java_with_context(
                        file_info["content"], 
                        file_info["filename"],
                        project_context,
                        include_comments,
                        generate_getters_setters,
                        use_java_conventions
                    )
                else:
                    result = convert_csharp_to_java(
                        file_info["content"], 
                        file_info["filename"],
                        include_comments,
                        generate_getters_setters,
                        use_java_conventions
                    )
                
                result.update({
                    "original_filename": file_info["filename"],
                    "java_filename": file_info["filename"].replace(".cs", ".java"),
                    "original_content": file_info["content"],
                    "zip_source": file_info.get("zip_source", None),
                })
                conversion_results.append(result)

            progress_bar.progress(1.0)
            status_text.text("변환 완료!")

            st.session_state.conversion_results = conversion_results
            success_count = len([r for r in conversion_results if "오류" not in r["java_code"]])
            st.session_state.conversion_stats = {
                "total_files": len(conversion_results),
                "success_rate": ((success_count / len(conversion_results)) * 100 if conversion_results else 0),
                "last_conversion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "used_project_context": bool(project_context),
                "conversion_options": {
                    "include_comments": include_comments,
                    "generate_getters_setters": generate_getters_setters,
                    "use_java_conventions": use_java_conventions,
                    "use_project_context": use_project_context
                }
            }
            
            if project_context:
                st.success(f"🎉 프로젝트단위로 {len(extracted_files)}개 파일 변환 완료!")
            else:
                st.success(f"✅ {len(extracted_files)}개 파일 변환 완료!")


# 변환 결과 탭
def conversion_results_tab():
    st.markdown("### 변환 결과 및 분석")

    if (
        "conversion_results" not in st.session_state
        or not st.session_state.conversion_results
    ):
        st.info("변환할 파일을 업로드하고 변환을 진행해주세요.")
        return

    results = st.session_state.conversion_results

    # 원본 파일명 추출
    original_name = "converted_files"
    if "project_structure" in st.session_state and st.session_state.project_structure:
        original_name = list(st.session_state.project_structure.keys())[0].replace(
            ".zip", ""
        )
    elif results:
        original_name = results[0]["original_filename"].replace(".cs", "")

    # 변환 옵션 표시
    if "conversion_stats" in st.session_state and "conversion_options" in st.session_state.conversion_stats:
        options = st.session_state.conversion_stats["conversion_options"]
        st.markdown("#### 적용된 변환 옵션")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            status = "✅" if options.get("include_comments") else "❌"
            st.markdown(f"{status} **주석 포함**")
        with col2:
            status = "✅" if options.get("generate_getters_setters") else "❌"
            st.markdown(f"{status} **Getter/Setter**")
        with col3:
            status = "✅" if options.get("use_java_conventions") else "❌"
            st.markdown(f"{status} **Java 컨벤션**")
        with col4:
            status = "✅" if options.get("use_project_context") else "❌"
            st.markdown(f"{status} **프로젝트 분석**")

    # 변환 통계
    st.markdown("#### 변환 통계")
    success_count = len([r for r in results if "오류" not in r["java_code"]])
    success_rate = (success_count / len(results)) * 100 if results else 0
    total_warnings = sum(len(r.get("warnings", [])) for r in results)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 파일 수", len(results))
    with col2:
        st.metric("성공한 변환", success_count)
    with col3:
        st.metric("성공률", f"{success_rate:.1f}%")
    with col4:
        st.metric("총 경고", total_warnings)

    # 상세 변환 결과
    st.markdown("#### 상세 변환 결과")
    for i, result in enumerate(results):
        with st.expander(
            f"📄 {result['original_filename']} → {result['java_filename']}",
            expanded=False,
        ):
            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("**원본 C# 코드**")
                st.code(
                    result.get("original_content", "// 원본 코드 없음"),
                    language="csharp",
                )

            with col2:
                st.markdown("**변환된 Java 코드**")
                st.code(result["java_code"], language="java")

            # 적용된 옵션 표시
            if result.get("applied_options"):
                st.markdown("**적용된 변환 옵션:**")
                options = result["applied_options"]
                option_items = []
                if options.get("include_comments"):
                    option_items.append("주석 포함")
                if options.get("generate_getters_setters"):
                    option_items.append("Getter/Setter 생성")
                if options.get("use_java_conventions"):
                    option_items.append("Java 네이밍 컨벤션")
                if option_items:
                    st.info(" | ".join(option_items))

            if result.get("imports"):
                st.markdown("**필요한 Import:**")
                for imp in result["imports"]:
                    st.code(imp, language="java")

            if result.get("conversion_notes"):
                st.info(f"**변환 노트:** {result['conversion_notes']}")

            if result.get("warnings"):
                st.markdown("**⚠️ 주의사항:**")
                for warning in result["warnings"]:
                    st.warning(warning)

            if result.get("type_mappings"):
                st.markdown("**타입 매핑:**")
                for cs_type, java_type in result["type_mappings"].items():
                    st.text(f"{cs_type} → {java_type}")

            st.download_button(
                label=f"{result['java_filename']} 다운로드",
                data=result["java_code"],
                file_name=result["java_filename"],
                mime="text/plain",
                key=f"download_{i}",
            )

    # 전체 다운로드
    st.markdown("#### 전체 결과 다운로드")

    # 프로젝트 구조가 있는 경우와 없는 경우 구분
    if "project_structure" in st.session_state and st.session_state.project_structure:
        # 완전한 프로젝트 구조 다운로드 (CS → Java 변환, 나머지 파일 유지)
        col1, col2 = st.columns(2)

        with col1:
            complete_zip_data = create_complete_project_zip(results)
            st.download_button(
                label="완전한 프로젝트 다운로드",
                data=complete_zip_data,
                file_name=f"{original_name}_project.zip",
                mime="application/zip",
                type="primary",
                help="원본 프로젝트 구조를 유지하면서 CS 파일만 Java로 변환",
            )

        with col2:
            java_only_zip_data = create_java_only_zip(results)
            st.download_button(
                label="Java 파일만 다운로드",
                data=java_only_zip_data,
                file_name=f"{original_name}_java.zip",
                mime="application/zip",
                help="변환된 Java 파일들만 포함",
            )
    else:
        # 개별 CS 파일만 업로드된 경우 (기존 방식)
        java_only_zip_data = create_java_only_zip(results)
        st.download_button(
            label="모든 Java 파일을 ZIP으로 다운로드",
            data=java_only_zip_data,
            file_name=f"{original_name}_java.zip",
            mime="application/zip",
            type="primary",
        )

    # 변환 통계
    if "conversion_stats" in st.session_state:
        st.markdown("#### 변환 통계")
        stats = st.session_state.conversion_stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 변환 파일", stats.get("total_files", 0))
        with col2:
            st.metric("성공률", f"{stats.get('success_rate', 0):.1f}%")
        with col3:
            st.metric("마지막 변환", stats.get("last_conversion", "없음"))


# 단일 코드 변환 탭
def instant_conversion_tab():
    st.markdown("### C# to Java 변환")

    col1, col2 = st.columns(2)

    with col1:
        if "instant_input_text" not in st.session_state:
            st.session_state.instant_input_text = ""

        csharp_input = st.text_area(
            "C# 코드를 입력하세요:",
            height=400,
            placeholder="""public class Person
{
    public string Name { get; set; }
    public int Age { get; set; }
    
    public string GetInfo()
    {
        return $"Name: {Name}, Age: {Age}";
    }
}""",
            key="instant_input_area",
            value=st.session_state.instant_input_text,
        )
        st.session_state.instant_input_text = csharp_input

        if st.button("단일 코드 변환", key="instant_convert", type="primary"):
            if csharp_input.strip():
                with st.spinner("변환 중..."):
                    result = convert_csharp_to_java(
                        csharp_input, 
                        "InstantConversion.cs"
                    )
                    st.session_state.instant_result = result
            else:
                st.warning("C# 코드를 입력해주세요.")

        if st.button(
            "초기화",
            key="reset_instant",
            help="현재 변환 결과와 입력 코드를 초기화합니다",
        ):
            if "instant_result" in st.session_state:
                del st.session_state.instant_result
            st.session_state.instant_input_text = ""
            st.success("초기화되었습니다!")
            st.rerun()

    with col2:
        st.markdown("**Java 변환 결과**")
        if "instant_result" in st.session_state:
            result = st.session_state.instant_result
            st.code(result["java_code"], language="java")

            if result["conversion_notes"]:
                st.info(f"**변환 노트:** {result['conversion_notes']}")

            if result["warnings"]:
                for warning in result["warnings"]:
                    st.warning(f"⚠️ {warning}")

            st.download_button(
                label="Java 파일 다운로드",
                data=result["java_code"],
                file_name="ConvertedCode.java",
                mime="text/plain",
            )
        else:
            st.info("왼쪽에 C# 코드를 입력하고 '단일 코드 변환' 버튼을 클릭하세요.")


# 코드 분석 탭
def code_analysis_tab():
    st.markdown("### C# 코드 분석 도구")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**분석할 C# 코드 입력**")

        if "analysis_input_text" not in st.session_state:
            st.session_state.analysis_input_text = ""

        analysis_input = st.text_area(
            "분석할 C# 코드를 입력하세요:",
            height=400,
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
    
    private void ProcessItem(OrderItem item)
    {
        // 복잡한 처리 로직
    }
}""",
            key="analysis_input_area",
            value=st.session_state.analysis_input_text,
        )
        st.session_state.analysis_input_text = analysis_input

        if st.button("코드 분석 시작", key="start_analysis", type="primary"):
            if analysis_input.strip():
                with st.spinner("코드 분석 중..."):
                    analysis_result = analyze_csharp_code(
                        analysis_input, "CodeAnalysis.cs"
                    )
                    if analysis_result:
                        st.session_state.current_analysis = analysis_result
                        st.success("분석 완료!")
                    else:
                        st.error("분석 중 오류가 발생했습니다.")
            else:
                st.warning("분석할 C# 코드를 입력해주세요.")

        if st.button(
            "초기화",
            key="reset_analysis",
            help="현재 분석 결과와 입력 코드를 초기화합니다",
        ):
            if "current_analysis" in st.session_state:
                del st.session_state.current_analysis
            st.session_state.analysis_input_text = ""
            st.success("초기화되었습니다!")
            st.rerun()

    with col2:
        st.markdown("**분석 결과**")
        if "current_analysis" in st.session_state and st.session_state.current_analysis:
            display_analysis_results(st.session_state.current_analysis)
        else:
            st.markdown(
                """
            <div class="analysis-card">
                <h4 style="color: #6c757d;">분석 준비 완료</h4>
                <p>왼쪽에 C# 코드를 입력하고 <strong>'코드 분석 시작'</strong> 버튼을 클릭하세요.</p>
                <p><strong>분석 항목:</strong> 리팩토링 제안, 잠재적 문제점, Java 변환 주의사항, 디자인 패턴, 코드 메트릭</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # 분석 히스토리
    st.markdown("#### 분석 히스토리")
    if "analysis_history" in st.session_state and st.session_state.analysis_history:
        recent_analyses = st.session_state.analysis_history[-5:]
        for i, analysis in enumerate(reversed(recent_analyses)):
            timestamp = analysis.get("timestamp", "Unknown")
            filename = analysis.get("filename", "Unknown")
            issues_count = len(analysis.get("potential_issues", []))

            with st.expander(
                f"분석 #{len(recent_analyses)-i} - {filename} ({timestamp})"
            ):
                st.metric("발견된 이슈", f"{issues_count}개")
                if analysis.get("summary"):
                    st.markdown(f"**요약:** {analysis['summary']}")
                if st.button(f"다시 분석", key=f"reanalyze_{i}"):
                    st.session_state.current_analysis = analysis
                    st.rerun()
    else:
        st.info("아직 분석 기록이 없습니다. 첫 번째 코드 분석을 시작해보세요!")


# 메인 함수
def main():
    apply_styles()

    # 헤더
    st.markdown(
        """
    <div class="main-header">
        <h1>C# to Java 코드 전환 AI AGENT</h1>
    </div>
    """,
        unsafe_allow_html=True,
    )

    setup_sidebar()

    # 탭 생성
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📁 파일 변환", "📈 변환 결과", "💬 단일 코드 변환", "🔍 코드 분석"]
    )

    with tab1:
        file_conversion_tab()
    with tab2:
        conversion_results_tab()
    with tab3:
        instant_conversion_tab()
    with tab4:
        code_analysis_tab()

    # 푸터
    st.markdown(
        """
    ---
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p><strong>C# to Java 코드 전환 AI AGENT</strong></p>
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()