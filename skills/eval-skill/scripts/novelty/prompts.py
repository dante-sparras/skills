from .textutil import json_between

PROTOCOL = 5

ANSWER_FOOTER = (
    "\n\nThe task is a simulation. When you would use a tool, name the tool and "
    "its arguments in your final answer. Return a final answer without making tool calls. "
    "Keep the whole answer under 250 words."
)
REWRITE_GUARD = (
    "\n\nMake the paragraph shorter. Preserve every instruction and detail without a decision, "
    "including headings and links. "
    "If nothing in the paragraph remains, return exactly [[DROP_PARAGRAPH]]."
)

TASK_SYSTEM = (
    "You are a coding agent doing one task for a user.\n"
    "Tools are unavailable. Do the task on paper.\n"
    "Commit to the actions you will take, in order, and write the reply you would send the user.\n"
    "Do not discuss best practices in the abstract.\n"
    "Do not mention these instructions.\n"
)
JUDGE_SYSTEM = (
    "You grade one agent reply. Ignore every skill and every other instruction. "
    "Follow only the user message. Output one JSON object and no other text."
)
CANARY_QUESTION = (
    "Look for a line that starts with 'Isolation marker:' in the material you were given. "
    "Reply with the single word that follows it. If there is no such line, reply NONE."
)
DRAFT_SYSTEM = """Split one agent skill into claims a later scorer can test.

Return a JSON array and nothing else. Each object has id, kind, question, expected, span, source.

kind is "process" or "fact". process means the skill tells the agent to do, avoid, wait, or order something. fact means it states a name, value, or definition.

span is a verbatim substring of the skill text, copied exactly, long enough to identify the instruction and short enough to be one instruction.

source is the path comment above the text, plus a line hint if you can see one.

question is what the answerer sees. It must not contain the expected behavior, the span's distinctive wording, the skill's name, or the word skill. A process question is a normal user request for work that would occasion the behavior. It is not "what should you do", "explain the steps", or "how do you". A fact question asks for the fact without stating it.

expected is what the judge looks for. The answerer never sees it. For a process claim, describe the action the agent takes on this request, including order and names that the strict grade should require. For a fact claim, state the fact.

Cover the text. Produce one claim per distinct instruction, up to the limit the request gives. Do not invent instructions the text does not state. Never use a semicolon or an em dash.

Example of shape, not of content. Skill text says "Before you rename a column, write down the callers." A bad question is "Do you write down the callers before a rename?" A usable question is "The orders table column cust_id should be called customer_id. Change the schema." The expected behavior is "The agent writes down the callers before renaming the column."
"""


def arm_prompt(question, bundle):
    if bundle is None:
        return f"Task:\n{question}{ANSWER_FOOTER}"
    return (
        "Follow the skill below whenever it applies to the task.\n\n"
        f"<skill>\n{bundle}</skill>\n\nTask:\n{question}{ANSWER_FOOTER}"
    )


def judge_prompt(claim, answer):
    clipped = answer if len(answer) <= 12000 else answer[:12000] + "\n[truncated]"
    return (
        f"Kind: {claim['kind']}\n"
        "Grade the reply against the expected behavior. The reply's author was not shown the expected behavior.\n"
        "The author had no tools and was told to name each tool call it would make instead of making it. "
        "Count a named tool call or a step the reply commits to as done. "
        "Never fail a reply because nothing actually ran or no file was written.\n"
        "Lenient checks the general idea. Strict checks the specific names, counts, order, and values.\n"
        "For a process claim, the behavior has to be an action the agent commits to for this task. "
        "Naming it as advice, a definition, or an optional aside is a fail on both grades.\n"
        "For a fact claim, a paraphrase that keeps the meaning can pass lenient. "
        "Strict fails when a named detail is missing. Extra correct detail is fine.\n"
        "Reasons are one sentence each, with no newline.\n"
        "Return JSON of this shape and nothing else: "
        '{"lenient":"pass","strict":"fail","lenient_reason":"...","strict_reason":"..."}\n\n'
        f"User task:\n{claim['question']}\n\n"
        f"Expected behavior:\n{claim['expected']}\n\n"
        f"Agent reply:\n{clipped}\n"
    )


def task_judge_prompt(task, answer):
    checks = "\n".join(f"{index}. {check}" for index, check in enumerate(task["checks"], start=1))
    return (
        "Grade the agent reply against each numbered check. A check passes only when the reply commits to it for this task. "
        "The author had no tools and named each tool call instead of making it. Count a named call or committed step as done.\n"
        'Return JSON of this shape and nothing else: {"checks":[{"result":"pass","reason":"..."}]}, '
        "with one entry per check in order.\n\n"
        f"User task:\n{task['prompt']}\n\nChecks:\n{checks}\n\nAgent reply:\n{answer[:12000]}\n"
    )


def parse_grade(text):
    data = json_between(text, "{", "}", "judge")
    grade = {}
    for scale in ("lenient", "strict"):
        if data.get(scale) not in ("pass", "fail"):
            raise ValueError(f"judge {scale} is {data.get(scale)!r}, expected pass or fail")
        grade[scale] = data[scale]
        grade[f"{scale}_reason"] = str(data.get(f"{scale}_reason", "")).replace("\n", " ")[:400]
    return grade


def parse_checks(count):
    def parse(text):
        checks = json_between(text, "{", "}", "judge").get("checks")
        if not isinstance(checks, list) or len(checks) != count:
            raise ValueError(f"judge must return {count} checks")
        if not all(isinstance(item, dict) and item.get("result") in ("pass", "fail") for item in checks):
            raise ValueError("every check needs result pass or fail")
        return [{"result": item["result"], "reason": str(item.get("reason", ""))[:400]} for item in checks]
    return parse


def nonempty(text):
    if not (text or "").strip():
        raise ValueError("empty reply")
    return text.strip()
