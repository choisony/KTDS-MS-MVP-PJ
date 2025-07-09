# 🔄 C# to Java 코드변환 및 분석 AI Agent

Azure OpenAI를 활용한 간단하고 실용적인 C# 코드를 Java로 변환하는 도구입니다.

## ✨ 주요 기능

- 🤖 **AI 기반 변환**: GPT-4.1을 활용한 지능형 C# → Java 변환
- 📁 **다중 파일 지원**: .cs 파일 및 프로젝트 .zip 파일 처리
- ⚡ **단일 코드 변환**: 코드 입력 즉시 변환 결과 확인
- 📊 **변환 분석**: 상세한 변환 노트 및 경고사항 제공
- 💾 **결과 다운로드**: 개별 파일 또는 전체 ZIP 다운로드

## 🚀 설치 및 실행

### 1. 프로젝트 설정
```bash
# 저장소 클론
git clone <your-repo-url>
cd csharp-java-converter

# 가상환경 생성
python -m venv venv
Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정
`.env` 파일을 생성하고 Azure OpenAI 정보를 입력:

```bash
OPENAI_API_KEY=your-azure-openai-api-key
AZURE_ENDPOINT=https://your-resource-name.openai.azure.com/
OPENAI_API_TYPE=azure
OPENAI_API_VERSION=2024-02-01
DEPLOYMENT_NAME=your-gpt4-deployment-name
```

### 3. 애플리케이션 실행
```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501`로 접속하세요.

## 📖 사용 방법

### 1. 파일 업로드 변환
1. **파일 변환** 탭 선택
2. C# 파일(.cs) 또는 프로젝트(.zip) 업로드
3. 변환 옵션 설정 (사이드바)
4. "🚀 변환 시작" 버튼 클릭
5. 결과 확인 및 다운로드

### 2. 변환 결과 분석
1. **변환 결과** 탭에서 상세 분석 확인
2. 성공률, 경고사항 등 통계 정보 제공
3. 개별 또는 전체 파일 다운로드

### 3. 단일 코드 변환
1. **단일 코드 변환** 탭 선택
2. 왼쪽에 C# 코드 입력
3. "⚡ 즉시 변환" 버튼 클릭
4. 오른쪽에서 Java 변환 결과 확인

### 4. 코드 분석
1. **코드 분석** 탭 선택
2. 왼쪽에 C# 코드 입력
3. "코드 분석시작" 버튼 클릭
4. 오른쪽에서 코드 분석 결과 확인

## 🎯 변환 기능

### 지원하는 변환:
- ✅ **Properties** → getter/setter 메서드
- ✅ **LINQ** → Stream API
- ✅ **string** → String
- ✅ **var** → 명시적 타입
- ✅ **PascalCase** → camelCase
- ✅ **using statements** → try-with-resources
- ✅ **async/await** → CompletableFuture

### 변환 예시:
**C# 입력:**
```csharp
public class Person
{
    public string Name { get; set; }
    public int Age { get; set; }
    
    public string GetInfo()
    {
        return $"Name: {Name}, Age: {Age}";
    }
}
```

**Java 출력:**
```java
public class Person {
    private String name;
    private int age;
    
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
    
    public int getAge() {
        return age;
    }
    
    public void setAge(int age) {
        this.age = age;
    }
    
    public String getInfo() {
        return String.format("Name: %s, Age: %d", name, age);
    }
}
```

## 🔧 Azure 배포

### Azure Web App에 배포:
```bash
# Azure CLI 로그인
az login

# 리소스 그룹 생성
az group create --name csharp-java-converter-rg --location "East US"

# Web App 생성
az webapp create \
  --resource-group csharp-java-converter-rg \
  --plan myAppServicePlan \
  --name csharp-java-converter \
  --runtime "PYTHON|3.9"

# 환경 변수 설정
az webapp config appsettings set \
  --resource-group csharp-java-converter-rg \
  --name csharp-java-converter \
  --settings OPENAI_API_KEY="your-key" AZURE_ENDPOINT="your-endpoint"
```

## 📊 성능 및 제한사항

### 성능:
- **변환 속도**: 평균 3-5초/파일
- **지원 파일 크기**: 최대 1MB/파일
- **동시 처리**: 최대 50개 파일

### 제한사항:
- P/Invoke 코드는 수동 변환 필요
- WPF/WinForms UI 코드는 미지원
- 복잡한 제네릭 제약사항은 검토 필요

