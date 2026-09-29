"""Shared pytest fixtures — offline fixture projects per SPEC."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    return tmp_path


def write_files(root: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content), encoding="utf-8")
    return root


@pytest.fixture
def chatbot_project(tmp_path: Path) -> Path:
    """Project with openai dep + chatbot signals -> transparency tier."""
    return write_files(tmp_path / "chatbot", {
        "requirements.txt": """
            flask>=3
            openai>=1.0
            requests
        """,
        "app.py": """
            from openai import OpenAI
            client = OpenAI()
            SYSTEM_PROMPT = "You are a helpful assistant."
            def chat(user_msg):
                messages = [{"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_msg}]
                return client.chat.completions.create(model="gpt-4o", messages=messages)
        """,
    })


@pytest.fixture
def plain_project(tmp_path: Path) -> Path:
    """Project with a torch dep but no risk signals -> limited tier."""
    return write_files(tmp_path / "plain", {
        "requirements.txt": """
            numpy
            torch
        """,
        "train.py": """
            import torch
            x = torch.randn(3, 3)
            print(x.mean())
        """,
    })


@pytest.fixture
def no_ai_project(tmp_path: Path) -> Path:
    """Project with no AI signals at all -> none tier."""
    return write_files(tmp_path / "webapp", {
        "package.json": """
            {
              "name": "webapp",
              "dependencies": { "express": "^4.0.0", "lodash": "^4.17.0" }
            }
        """,
        "server.js": """
            const express = require("express");
            const app = express();
            app.get("/", (req, res) => res.send("hi"));
            app.listen(3000);
        """,
    })


@pytest.fixture
def prohibited_project(tmp_path: Path) -> Path:
    """Project with social-scoring signals -> prohibited tier."""
    return write_files(tmp_path / "badcorp", {
        "requirements.txt": """
            scikit-learn
        """,
        "scoring.py": """
            def compute_social_score(citizen):
                # social_score based on behaviour data
                score = citizen.purchases * 0.3 + citizen.posts * 0.7
                return score
        """,
    })


@pytest.fixture
def hr_project(tmp_path: Path) -> Path:
    """Project with resume screening -> high-risk tier."""
    return write_files(tmp_path / "hrtool", {
        "pyproject.toml": """
            [project]
            name = "hrtool"
            dependencies = ["transformers>=4", "fastapi"]
        """,
        "screen.py": """
            def resume_screen(cv_text):
                # candidate_rank via model
                model = load_model()
                return model.predict(cv_text)
        """,
    })


@pytest.fixture
def node_project(tmp_path: Path) -> Path:
    """Node.js project with AI deps -> detection via package.json."""
    return write_files(tmp_path / "nodeapp", {
        "package.json": """
            {
              "name": "nodeapp",
              "dependencies": {
                "@anthropic-ai/sdk": "^0.30.0",
                "express": "^4.0.0"
              }
            }
        """,
        "bot.js": """
            const Anthropic = require("@anthropic-ai/sdk");
            const client = new Anthropic();
        """,
    })


@pytest.fixture
def deepfake_project(tmp_path: Path) -> Path:
    """Project with face-swap/video-gen signals -> transparency findings."""
    return write_files(tmp_path / "dfake", {
        "requirements.txt": """
            torch
            diffusers
        """,
        "swap.py": """
            from diffusers import StableDiffusionPipeline
            def face_swap(img):
                # deepfake pipeline
                return run(img)
        """,
    })
