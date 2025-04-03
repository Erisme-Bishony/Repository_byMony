import os
import json
import sqlite3
import subprocess
import asyncio
import hashlib
from datetime import datetime
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
import os



load_dotenv()

# 确保data目录存在
DATA_DIR = "../data"
LOG_FILE = os.path.join(DATA_DIR, "logs.txt")
SCRIPTS_DIR = os.path.join(DATA_DIR, "scripts")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
KNOWLEDGE_DIR = os.path.join(DATA_DIR, "knowledge")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SCRIPTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

# 从环境变量中读取API密钥
grok_api_key = os.getenv("Grok_Api_Key")
openai_api_key = os.getenv("ChatGpt_Api_Key")


if not grok_api_key or not openai_api_key:
    raise ValueError("环境变量 GROK_API_KEY 或 OPENAI_API_KEY 未设置")

# 初始化Grok客户端（AI秘书）
secretary_client = OpenAI(
    api_key=grok_api_key,
    base_url="https://api.x.ai/v1"
)
async_secretary_client = AsyncOpenAI(
    api_key=grok_api_key,
    base_url="https://api.x.ai/v1"
)

# 初始化讨论组成员（OpenAI/ChatGPT）
discussion_group = {
    "OpenAI-o3-mini": {
        "client": OpenAI(
            api_key=openai_api_key,
            base_url="https://api.openai.com/v1"
        ),
        "async_client": AsyncOpenAI(
            api_key=openai_api_key,
            base_url="https://api.openai.com/v1"
        ),
        "model": "o3-mini",
        "specialty": "编码和逻辑推理"
    }
}



# 日志记录函数
def log_interaction(user_input, ai_name, response):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] User: {user_input} | {ai_name}: {response}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)


# 知识库操作
def save_to_knowledge(task, discussion_log, final_result):
    task_hash = hashlib.md5(task.encode()).hexdigest()
    knowledge_file = os.path.join(KNOWLEDGE_DIR, f"task_{task_hash}.json")
    with open(knowledge_file, "w", encoding="utf-8") as f:
        json.dump({"task": task, "discussion_log": discussion_log, "result": final_result}, f)


def load_from_knowledge(task):
    task_hash = hashlib.md5(task.encode()).hexdigest()
    knowledge_file = os.path.join(KNOWLEDGE_DIR, f"task_{task_hash}.json")
    if os.path.exists(knowledge_file):
        with open(knowledge_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data["result"], data["discussion_log"]
    return None, None


# 创建文件函数
def create_file(filename, content, directory=SCRIPTS_DIR):
    file_path = os.path.join(directory, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path


# 读取文件函数
def read_file(filename, directory=SCRIPTS_DIR):
    file_path = os.path.join(directory, filename)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f"文件内容:\n{f.read()}"
    return f"文件不存在: {file_path}"


# 运行Python代码（增加安全性）
def run_code(filename):
    file_path = os.path.join(SCRIPTS_DIR, filename)
    if not os.path.exists(file_path):
        return f"文件不存在: {file_path}"
    try:
        result = subprocess.run(
            ["python", file_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return f"运行成功:\n{result.stdout}"
        else:
            return f"运行失败:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "运行超时"
    except Exception as e:
        return f"运行错误: {e}"


# 异步调用AI
async def ask_ai_async(client, model, name, user_input):
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": user_input}]
        )
        response_text = response.choices[0].message.content
        log_interaction(user_input, name, response_text)
        return response_text
    except Exception as e:
        error_msg = f"{name} 调用失败: {e}"
        log_interaction(user_input, name, error_msg)
        return error_msg


# 同步调用AI（用于秘书）
def ask_ai(client, model, name, user_input):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": user_input}]
        ).choices[0].message.content
        log_interaction(user_input, name, response)
        return response
    except Exception as e:
        error_msg = f"{name} 调用失败: {e}"
        log_interaction(user_input, name, error_msg)
        return error_msg


# 评估讨论组回答质量
def evaluate_responses(responses):
    if len(responses) < 2:
        return 0
    words1 = set(responses[0].split())
    words2 = set(responses[1].split())
    overlap = len(words1.intersection(words2)) / min(len(words1), len(words2))
    return overlap


# AI讨论组逻辑（并行讨论）
async def ai_discussion_group(topic, rounds=2):
    discussion_log = [f"## 讨论组记录\n\n**讨论主题**: {topic}\n\n"]
    current_input = topic

    for i in range(rounds):
        tasks = []
        for ai_name, ai_info in discussion_group.items():
            prompt = f"当前讨论主题: {topic}\n之前的讨论: {current_input}\n请提出你的看法或解决方案（你的专长是: {ai_info['specialty']}）。"
            task = ask_ai_async(ai_info["async_client"], ai_info["model"], ai_name, prompt)
            tasks.append((ai_name, task))

        responses = await asyncio.gather(*[task for _, task in tasks])
        for (ai_name, _), response in zip(tasks, responses):
            discussion_log.append(f"### Round {i + 1} - {ai_name}\n{response}\n\n")
            current_input = response

        # 动态调整轮数
        overlap = evaluate_responses(responses)
        if overlap > 0.8:
            discussion_log.append(f"### 提前结束\n讨论组意见一致（相似度: {overlap:.2f}），提前结束讨论。\n\n")
            break

    return discussion_log


# AI秘书逻辑
async def ai_secretary(user_input, feedback=None):
    # 检查知识库
    cached_result, cached_log = load_from_knowledge(user_input)
    if cached_result:
        return {
            "result": f"从知识库中找到结果:\n{cached_result}",
            "discussion_log": cached_log
        }

    # AI秘书解析用户指令
    secretary_prompt = f"用户输入: {user_input}\n" \
                       f"你是我的AI秘书，请解析我的指令，决定是否需要讨论组介入，并制定任务计划。\n" \
                       f"如果需要讨论，提取讨论主题并指定讨论轮数；如果需要直接回答，直接提供答案；" \
                       f"如果需要生成代码，明确代码需求。\n" \
                       f"如果有用户反馈: {feedback if feedback else '无'}，请根据反馈调整策略（例如增加讨论轮数）。"
    secretary_plan = ask_ai(secretary_client, "grok-2-1212", "Secretary", secretary_prompt)

    # 记录秘书的计划
    discussion_log = [f"# AI秘书工作记录\n\n**用户指令**: {user_input}\n\n## 秘书计划\n{secretary_plan}\n\n"]

    # 根据秘书计划执行任务
    if "需要讨论" in secretary_plan.lower():
        topic = user_input if user_input.startswith("讨论 ") else user_input
        if topic.startswith("讨论 "):
            topic = topic.split(" ", 1)[1]
        rounds = 2
        if feedback and "评分: 3" in feedback:
            rounds = 3

        discussion_log.extend(await ai_discussion_group(topic, rounds))

        summary_prompt = f"以下是讨论组的讨论记录:\n{''.join(discussion_log)}\n" \
                         f"作为AI秘书，请总结讨论结果，并提出最终方案（如果需要，生成代码）。"
        final_response = ask_ai(secretary_client, "grok-2-1212", "Secretary", summary_prompt)
        discussion_log.append(f"## 最终方案 - 秘书\n{final_response}\n\n")
    else:
        final_response = ask_ai(secretary_client, "grok-2-1212", "Secretary", user_input)
        discussion_log.append(f"## 直接回答 - 秘书\n{final_response}\n\n")

    # 保存讨论记录为Markdown文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"report_{timestamp}.md"
    report_path = create_file(report_filename, "".join(discussion_log), REPORTS_DIR)

    # 检查最终方案是否包含代码
    code_output = ""
    if "```python" in final_response:
        code_start = final_response.find("```python") + 9
        code_end = final_response.find("```", code_start)
        code = final_response[code_start:code_end].strip()

        code_filename = f"solution_{timestamp}.py"
        code_path = create_file(code_filename, code)

        code_output = f"\n生成代码并运行:\n文件: {code_path}\n{run_code(code_filename)}"

    # 保存到知识库
    final_result = f"{''.join(discussion_log)}{code_output}"
    save_to_knowledge(user_input, discussion_log, final_result)

    return {
        "result": f"任务完成！\n{final_result}\n报告已保存到: {report_path}",
        "discussion_log": discussion_log
    }


# 主逻辑
async def process_input(user_input, feedback=None):
    if user_input.startswith("创建文件 "):
        parts = user_input.split(" ", 2)
        if len(parts) == 3:
            filename, content = parts[1], parts[2]
            return {"result": f"文件已创建: {create_file(filename, content)}", "discussion_log": []}

    elif user_input.startswith("读取文件 "):
        filename = user_input.split(" ", 1)[1]
        return {"result": read_file(filename), "discussion_log": []}

    else:
        return await ai_secretary(user_input, feedback)

