"""Rule tables: AI library registry, banned-practice / high-risk / Art.50 signal rules.

All rules are heuristic data tables. Each rule explains WHY it triggers and cites
the relevant EU AI Act article so every finding is auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# AI library / provider registry (F1)
# ---------------------------------------------------------------------------

# capability -> list of package names (lowercase, normalized)
AI_LIBRARY_REGISTRY: dict[str, list[str]] = {
    "llm-provider-sdk": [
        "openai", "anthropic", "google-generativeai", "google-genai", "genai",
        "cohere", "mistralai", "mistral-ai", "ai21", "replicate", "together",
        "groq", "fireworks-ai", "deepseek", "boto3-bedrock", "azure-ai-inference",
        "@openai/agents", "@anthropic-ai/sdk", "@google/generative-ai", "openai-js",
        "@ai-sdk/openai", "@ai-sdk/anthropic", "ai", "langchain-openai",
        "langchain-anthropic", "langchain-google-genai", "ollama", "ollama-python",
    ],
    "local-model-runtime": [
        "transformers", "llama-cpp-python", "llama.cpp", "ctransformers", "ctranslate2", "onnxruntime",
        "onnxruntime-gpu", "mlx", "mlx-lm", "gpt4all", "localai", "koboldcpp",
        "vllm", "text-generation-inference", "whisper.cpp", "whisper-rs",
    ],
    "ml-framework": [
        "torch", "tensorflow", "tensorflow-cpu", "jax", "keras", "scikit-learn",
        "xgboost", "lightgbm", "catboost", "paddlepaddle", "mxnet", "flax",
        "candle-core", "burn", "tch", "tfjs-node", "brain.js", "ml5",
    ],
    "agent-framework": [
        "langchain", "langgraph", "llamaindex", "llama-index", "llama_index",
        "autogen", "pyautogen", "crewai", "semantic-kernel", "haystack-ai",
        "haystack", "dspy", "agno", "smolagents", "swarm", "guidance", "mastra",
        "langflow", "flowise", "autogpt", "superagent",
    ],
    "speech": [
        "elevenlabs", "elevenlabs-python", "openai-whisper", "faster-whisper",
        "whisperx", "piper-tts", "pyttsx3", "speechrecognition", "vosk",
        "coqui-tts", "tts", "bark", "resemblyzer", "pyannote.audio",
        "@elevenlabs/elevenlabs-js", "deepgram", "assemblyai",
    ],
    "vision": [
        "opencv-python", "opencv-python-headless", "dlib", "face-recognition",
        "insightface", "mediapipe", "yolo", "ultralytics", "mmdetection",
        "detectron2", "albumentations", "torchvision", "pillow-heif",
        "@tensorflow-models/coco-ssd", "@vladmandic/face-api", "face-api.js",
        "supervision", "roboflow", "clarifai",
    ],
    "embeddings-search": [
        "sentence-transformers", "chromadb", "chroma", "pinecone-client", "pinecone",
        "weaviate-client", "qdrant-client", "qdrant", "milvus", "pymilvus",
        "pgvector", "faiss-cpu", "faiss-gpu", "annoy", "lancedb", "txtai",
    ],
    "image-generation": [
        "diffusers", "stability-sdk", "stable-diffusion-sdk", "comfyui",
        "invokeai", "automatic1111", "kohya-ss", "midjourney-api", "leonardoai",
    ],
}

# Reverse index built lazily
_PACKAGE_TO_CAPABILITY: dict[str, str] | None = None


def package_capability(pkg: str) -> str | None:
    """Return the capability category for a normalized package name, else None."""
    global _PACKAGE_TO_CAPABILITY
    if _PACKAGE_TO_CAPABILITY is None:
        _PACKAGE_TO_CAPABILITY = {}
        for cap, pkgs in AI_LIBRARY_REGISTRY.items():
            for p in pkgs:
                _PACKAGE_TO_CAPABILITY[p.lower()] = cap
    return _PACKAGE_TO_CAPABILITY.get(pkg.lower())


# ---------------------------------------------------------------------------
# Code heuristic signals (F1)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CodeSignal:
    """A regex-based source-code heuristic signal."""
    id: str
    pattern: str  # regex, applied per file (case-insensitive)
    capability: str
    note: str


CODE_SIGNALS: list[CodeSignal] = [
    CodeSignal("llm-api-openai", r"openai\.(ChatCompletion|Client|chat\.completions|OpenAI)|api\.openai\.com|from openai import|import openai\b|OpenAI\s*\(", "llm-provider-sdk", "OpenAI API usage"),
    CodeSignal("llm-api-anthropic", r"anthropic\.(Client|Anthropic|messages\.create)|api\.anthropic\.com|from anthropic import|import anthropic\b|Anthropic\s*\(", "llm-provider-sdk", "Anthropic API usage"),
    CodeSignal("llm-api-generic", r"completions?\.create\s*\(|chat\.completions|generate_text\s*\(|/v1/chat/completions", "llm-provider-sdk", "Generic LLM completion call"),
    CodeSignal("ollama-local", r"localhost:11434|ollama\.(chat|generate|Client)|127\.0\.0\.1:11434", "local-model-runtime", "Ollama local model endpoint"),
    CodeSignal("hf-transformers", r"from transformers import|AutoModelForCausalLM|AutoTokenizer|pipeline\(\s*[\"'](text-generation|automatic-speech-recognition)", "local-model-runtime", "HuggingFace transformers usage"),
    CodeSignal("prompt-construction", r"(system_prompt|SYSTEM_PROMPT|prompt_template|PromptTemplate|messages\s*=\s*\[\s*\{\s*[\"']role[\"'])", "agent-framework", "Prompt/message construction for an LLM"),
    CodeSignal("speech-synthesis", r"(text_to_speech|textToSpeech|synthesize_speech|elevenlabs|piper.*tts|SpeechSynthesizer)", "speech", "Text-to-speech synthesis"),
    CodeSignal("speech-recognition", r"(speech_to_text|speechToText|whisper|transcribe_audio|recognize_audio|SpeechRecognizer)", "speech", "Speech-to-text recognition"),
    CodeSignal("face-recognition", r"(face_recognition|face_detection|facenet|face_recogni[sz]|dlib\.face|insightface|face-api)", "vision", "Facial recognition/detection"),
    CodeSignal("biometric-categorisation", r"(biometric.{0,30}(categor|classif|race|ethnicity|religion|political|sexual))", "vision", "Biometric categorisation signal (Art. 5 check)"),
    CodeSignal("emotion-recognition", r"(emotion[_ -]?recognition|affect[_ -]?ive[_ -]?computing|detect.{0,15}emotion|facial.{0,15}emotion|sentiment.{0,15}webcam)", "vision", "Emotion recognition signal (Art. 5 / Art. 50 check)"),
    CodeSignal("image-generation", r"(StableDiffusion|stable_diffusion|diffusers|text_to_image|textToImage|image_generation|ComfyUI|midjourney)", "image-generation", "Image generation"),
    CodeSignal("audio-generation", r"(music_gen|audio_generation|voice[_ -]?clon|bark\.generate|generate_speech)", "speech", "Audio/voice generation or cloning"),
    CodeSignal("deepfake-signals", r"(deepfake|face[_ -]?swap|faceswap|lip[_ -]?sync|video[_ -]?generation|text[_ -]?to[_ -]?video|sora|runway|kling|wan2|video_generate)", "image-generation", "Deepfake / video generation signal (Art. 50(4) check)"),
    CodeSignal("social-scoring", r"(social[_ -]?score|social[_ -]?credit|credit[_ -]?score.{0,40}(behavi|social)|trust[_ -]?score.{0,40}(citizen|user|person))", "prohibited-candidate", "Social scoring signal — PROHIBITED (Art. 5(1)(c))"),
    CodeSignal("subliminal-manipulation", r"(subliminal|manipulat.{0,30}technique|dark[_ -]?pattern.{0,30}(llm|ai|model)|exploit.{0,30}vulnerabilit.{0,30}(age|disab))", "prohibited-candidate", "Manipulative/subliminal technique signal (Art. 5(1)(a)-(b))"),
    CodeSignal("scraped-facial-db", r"(scrape.{0,30}facial|facial.{0,30}scrap|untargeted.{0,30}facial|clearview)", "prohibited-candidate", "Untargeted facial-image scraping signal (Art. 5(1)(e))"),
    CodeSignal("rbi-public-space", r"(real[_ -]?time.{0,30}biometric|remote[_ -]?biometric[_ -]?identification|rbi.{0,20}public|cctv.{0,30}face)", "prohibited-candidate", "Real-time remote biometric ID in public spaces signal (Art. 5(1)(h))"),
    CodeSignal("hr-screening", r"(resume[_ -]?(screen|pars|rank)|cv[_ -]?(screen|rank|filter)|candidate[_ -]?(rank|score|screen)|applicant[_ -]?(track|score|filter)|hire.{0,20}(score|model|ai)|recruitment.{0,20}(score|model|ai|llm))", "high-risk-candidate", "Employment/HR screening signal (Annex III(4))"),
    CodeSignal("credit-scoring", r"(credit[_ -]?(scor|risk|worthiness)|loan[_ -]?(approv|scor|eligib)|solvency)", "high-risk-candidate", "Credit scoring signal (Annex III(5)(b))"),
    CodeSignal("education-assessment", r"(student[_ -]?(assess|score|evaluat|monitor)|exam[_ -]?(scor|proctor|evaluat)|proctoring|admission.{0,20}(score|model|ai))", "high-risk-candidate", "Education assessment signal (Annex III(3))"),
    CodeSignal("essential-services", r"(insurance[_ -]?(pricing|risk|scor)|health[_ -]?insurance.{0,20}(eligib|scor)|benefit[_ -]?(eligib|allocat)|public[_ -]?assistance.{0,20}(eligib|scor)|triage[_ -]?(model|ai|score)|dispatch[_ -]?(emergenc|ambulance|police).{0,20}(ai|model|priorit))", "high-risk-candidate", "Essential services eligibility signal (Annex III(5))"),
    CodeSignal("critical-infrastructure", r"(safety[_ -]?component.{0,30}(infrastructure|traffic|water|gas|electric|nuclear)|critical[_ -]?infrastructure.{0,30}(ai|model|predict))", "high-risk-candidate", "Critical infrastructure signal (Annex III(2))"),
    CodeSignal("law-enforcement", r"(crime[_ -]?(risk|predict)|predictive[_ -]?policing|offender[_ -]?(risk|recidiv)|evidence[_ -]?reliability)", "high-risk-candidate", "Law enforcement signal (Annex III(6))"),
    CodeSignal("migration-border", r"(asylum[_ -]?(applicat|risk|screen)|visa[_ -]?(risk|screen|approv)|border[_ -]?(surveillance|risk)|migration[_ -]?risk)", "high-risk-candidate", "Migration/border signal (Annex III(7))"),
    CodeSignal("judicial-democratic", r"(judicial.{0,20}(ai|model|decision)|court.{0,20}(outcome|decision).{0,20}(predict|model)|election.{0,20}(influence|outcome).{0,20}(model|ai))", "high-risk-candidate", "Judicial/democratic process signal (Annex III(8))"),
]

# ---------------------------------------------------------------------------
# Risk-tier rule tables (F2)
# ---------------------------------------------------------------------------

RISK_PROHIBITED = "prohibited"
RISK_HIGH = "high-risk"
RISK_TRANSPARENCY = "transparency"
RISK_LIMITED = "limited"
RISK_NONE = "none"

RISK_ORDER = {RISK_NONE: 0, RISK_LIMITED: 1, RISK_TRANSPARENCY: 2, RISK_HIGH: 3, RISK_PROHIBITED: 4}

# Capability -> default transparency obligation (Art. 50)
CAPABILITY_TRANSPARENCY: dict[str, tuple[str, str]] = {
    # capability -> (article, obligation summary)
    "llm-provider-sdk": ("Art. 50(1)/(2)", "If used in a chatbot or to generate synthetic text, disclose AI interaction and mark synthetic output machine-readably."),
    "agent-framework": ("Art. 50(1)/(2)", "Conversational agents must disclose they are AI; generated content must be marked."),
    "speech": ("Art. 50(2)/(4)", "Synthetic audio must be marked machine-readably; deepfake audio must be disclosed."),
    "image-generation": ("Art. 50(2)/(4)", "Synthetic images/video must be marked machine-readably; deepfakes must be disclosed."),
    "local-model-runtime": ("Art. 50(2)", "If the model generates synthetic content, mark it machine-readably."),
}

# Explicit feature flags from aiact-check.toml (F7) that force transparency tier
TRANSPARENCY_FLAGS: dict[str, tuple[str, str]] = {
    "chatbot": ("Art. 50(1)", "System interacts directly with natural persons — must inform users they are interacting with AI unless obvious."),
    "generates_content": ("Art. 50(2)", "System generates synthetic content — output must be marked as artificially generated in a machine-readable format."),
    "deepfake": ("Art. 50(4)", "System generates deepfakes — must be disclosed as artificially generated/manipulated."),
}

HIGH_RISK_DOMAINS: dict[str, str] = {
    "biometrics": "Annex III(1) — biometrics",
    "critical-infrastructure": "Annex III(2) — critical infrastructure safety components",
    "education": "Annex III(3) — education and vocational training",
    "employment": "Annex III(4) — employment, workers management, self-employment access",
    "essential-services": "Annex III(5) — access to essential private/public services (incl. credit scoring, insurance pricing, emergency dispatch)",
    "law-enforcement": "Annex III(6) — law enforcement",
    "migration": "Annex III(7) — migration, asylum and border control",
    "judicial": "Annex III(8) — judicial and democratic processes",
}

# Map code-signal ids to high-risk domains for classification
SIGNAL_TO_DOMAIN: dict[str, str] = {
    "hr-screening": "employment",
    "credit-scoring": "essential-services",
    "education-assessment": "education",
    "essential-services": "essential-services",
    "critical-infrastructure": "critical-infrastructure",
    "law-enforcement": "law-enforcement",
    "migration-border": "migration",
    "judicial-democratic": "judicial",
}

PROHIBITED_ARTICLES: dict[str, str] = {
    "social-scoring": "Art. 5(1)(c) — social scoring by/on behalf of public authorities or private actors leading to detrimental treatment",
    "subliminal-manipulation": "Art. 5(1)(a)-(b) — subliminal or purposefully manipulative techniques causing significant harm",
    "scraped-facial-db": "Art. 5(1)(e) — untargeted scraping of facial images from internet/CCTV for facial recognition databases",
    "rbi-public-space": "Art. 5(1)(h) — real-time remote biometric identification in publicly accessible spaces for law enforcement (narrow exceptions)",
    "emotion-recognition": "Art. 5(1)(f) — emotion inference in workplace/education settings (check context!)",
    "biometric-categorisation": "Art. 5(1)(g) — biometric categorisation to infer race, political opinions, union membership, religious beliefs, sex life/orientation",
}

# ---------------------------------------------------------------------------
# Deadlines (F4)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Deadline:
    date: str  # ISO
    title: str
    detail: str


DEADLINES: list[Deadline] = [
    Deadline("2025-02-02", "Prohibitions + AI literacy in force",
             "Art. 5 prohibited practices and Art. 4 AI literacy obligations apply."),
    Deadline("2025-08-02", "GPAI obligations + governance + penalties",
             "General-purpose AI model provider obligations (Art. 53), governance bodies, penalty regime."),
    Deadline("2026-08-02", "Article 50 transparency + general application",
             "Transparency obligations for chatbots and synthetic content; most remaining provisions apply."),
    Deadline("2027-08-02", "Legacy GPAI models must comply",
             "GPAI models placed on the market before 2025-08-02 must be brought into compliance."),
    Deadline("2027-12-02", "Legacy high-risk systems must comply",
             "High-risk (Annex III) systems placed on the market before 2026-08-02 must comply."),
]


@dataclass
class Obligation:
    """One concrete compliance obligation (F3)."""
    id: str
    article: str
    applies_to: str  # provider | deployer | both
    text: str
    deadline: str
    status: str = "todo"
    severity: str = "info"  # info | due-soon | action-required
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "article": self.article,
            "appliesTo": self.applies_to,
            "text": self.text,
            "deadline": self.deadline,
            "status": self.status,
            "severity": self.severity,
            "notes": list(self.notes),
        }


@dataclass
class Finding:
    """A scanner finding: what triggered, where, why, and how severe."""
    id: str
    severity: str  # prohibited | high-risk | transparency | info
    title: str
    article: str
    why: str
    locations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "title": self.title,
            "article": self.article,
            "why": self.why,
            "locations": list(self.locations),
        }
