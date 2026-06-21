"""
api_skill_demo.py
演示如何用 Anthropic Python SDK 集成自定义 Skill

环境配置：
  pip install anthropic python-dotenv
  export ANTHROPIC_API_KEY=sk-ant-...

需要的 Beta 头：
  - code-execution-2025-01-01   （Code Execution Tool）
  - skills-2025-01-01            （Skills API）
  - files-api-2025-04-14         （Files API）
"""

import os
import json
import time
import zipfile
import tempfile
from pathlib import Path
from anthropic import Anthropic
from anthropic import APIError, APIConnectionError, RateLimitError
from dotenv import load_dotenv

load_dotenv()

# ============ 配置 ============
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

BETAS = [
    "code-execution-2025-01-01",
    "skills-2025-01-01",
    "files-api-2025-04-14",
]


# ============ Step 1：上传 Skill ============
def upload_skill(skill_dir: str, skill_name: str) -> str:
    """
    上传一个 skill 目录，返回 skill_id
    Skill 必须打包成 zip 格式上传
    """
    skill_path = Path(skill_dir)
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill directory not found: {skill_dir}")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        zip_path = tmp.name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in skill_path.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(skill_path)
                zf.write(file, arcname)

    with open(zip_path, "rb") as f:
        skill = client.beta.skills.create(
            name=skill_name,
            skill_data=f,
            betas=BETAS,
        )

    print(f"✓ Skill uploaded")
    print(f"  ID      : {skill.id}")
    print(f"  Name    : {skill.name}")
    print(f"  Version : {skill.version}")

    os.unlink(zip_path)
    return skill.id


# ============ Step 2：调用带 Skill 的对话 ============
def chat_with_skill(
    skill_id: str,
    user_message: str,
    upload_files: list[str] = None,
    model: str = "claude-sonnet-4-5",
    max_tokens: int = 4096,
) -> str:
    """
    用指定 skill 进行对话

    Args:
        skill_id: 上传后获得的 skill ID
        user_message: 用户消息文本
        upload_files: 需要一并上传到沙箱的文件路径列表
        model: 使用的模型
        max_tokens: 最大 token 数

    Returns:
        Claude 的文本响应
    """
    # 1. 上传输入文件
    file_ids = []
    if upload_files:
        for file_path in upload_files:
            with open(file_path, "rb") as f:
                file_obj = client.beta.files.upload(file=f, betas=BETAS)
                file_ids.append(file_obj.id)
                print(f"✓ File uploaded: {file_obj.id} ({file_path})")

    # 2. 构造消息内容
    message_content = []
    for fid in file_ids:
        message_content.append({"type": "file", "file": {"file_id": fid}})
    message_content.append({"type": "text", "text": user_message})

    # 3. 调用 Messages API
    response = client.beta.messages.create(
        model=model,
        max_tokens=max_tokens,
        betas=BETAS,
        skills=[
            {"type": "custom", "skill_id": skill_id, "version": "latest"}
        ],
        tools=[{"type": "code_execution_20250101", "name": "code_execution"}],
        messages=[{"role": "user", "content": message_content}],
    )

    # 4. 提取响应
    text_parts = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
        elif block.type == "bash_code_execution_tool_result":
            if hasattr(block, "content") and hasattr(block.content, "content"):
                for result_block in block.content.content:
                    if hasattr(result_block, "file_id"):
                        text_parts.append(
                            f"[Generated file: {result_block.file_id}]"
                        )

    return "\n".join(text_parts)


# ============ Step 2b：流式响应 ============
def chat_with_skill_streaming(
    skill_id: str,
    user_message: str,
    model: str = "claude-sonnet-4-5",
    max_tokens: int = 4096,
):
    """流式响应版本——逐 token 输出"""
    with client.beta.messages.stream(
        model=model,
        max_tokens=max_tokens,
        betas=BETAS,
        skills=[{"type": "custom", "skill_id": skill_id, "version": "latest"}],
        tools=[{"type": "code_execution_20250101", "name": "code_execution"}],
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        print()


# ============ Step 3：下载沙箱输出 ============
def download_file(file_id: str, output_path: str):
    """从沙箱下载生成的文件"""
    file_content = client.beta.files.download(file_id=file_id, betas=BETAS)
    with open(output_path, "wb") as f:
        file_content.write_to_file(f.name)
    print(f"✓ Downloaded: {output_path}")


# ============ 管理 Skill ============
def list_my_skills():
    """列出我创建的所有 skill"""
    skills = client.beta.skills.list(betas=BETAS)
    for skill in skills.data:
        print(f"- {skill.name} ({skill.id}) v{skill.version}")


def get_skill_versions(skill_id: str):
    """查看 skill 的版本历史"""
    versions = client.beta.skills.versions.list(skill_id=skill_id, betas=BETAS)
    for v in versions.data:
        print(f"- {v.version} (created: {v.created_at})")


def delete_skill(skill_id: str):
    """删除一个 skill"""
    client.beta.skills.delete(skill_id=skill_id, betas=BETAS)
    print(f"✓ Skill deleted: {skill_id}")


# ============ 错误处理 ============
def safe_chat_with_skill(
    skill_id: str,
    user_message: str,
    max_retries: int = 3,
):
    """带错误处理和指数退避重试"""
    for attempt in range(max_retries):
        try:
            return chat_with_skill(skill_id, user_message)
        except RateLimitError:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"⏳ Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
        except APIConnectionError as e:
            print(f"⚠️ Connection error: {e}")
            raise
        except APIError as e:
            print(f"⚠️ API error: {e.status_code} - {e.message}")
            raise


# ============ 演示 ============
def main():
    print("=" * 60)
    print("API Skill Demo")
    print("=" * 60)

    # 列出已有 skill
    print("\n[1] 列出已上传的 skill")
    list_my_skills()

    # 上传 PDF 填表 skill
    print("\n[2] 上传 pdf-form-filler skill")
    skill_id = upload_skill(
        skill_dir="../pdf-form-filler",
        skill_name="PDF Form Filler",
    )

    # 用 skill 处理 PDF
    print("\n[3] 用 skill 处理 PDF")
    response = chat_with_skill(
        skill_id=skill_id,
        user_message=(
            "请提取这个 PDF 的所有表单字段，"
            "告诉我哪些是必填的。"
        ),
        upload_files=["./sample-form.pdf"],
    )

    print("\n" + "=" * 60)
    print("Claude's Response:")
    print("=" * 60)
    print(response)


if __name__ == "__main__":
    main()
