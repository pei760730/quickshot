#!/usr/bin/env python3
"""Improve a skill description based on eval results.

Takes eval results (from run_eval.py) and generates an improved description
by calling the Anthropic Python SDK (`pip install anthropic`).

Auth: the SDK default chain — ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, or an
`ant auth login` profile. (Pre-migration this script shelled out to `claude -p`
to reuse Claude Code session auth; the SDK path needs one of the above.)

Prompt caching: the stable prefix (task instructions + SKILL.md body) lives in
`system` with a cache_control breakpoint; per-iteration eval data goes in the
user turn. Across run_loop.py iterations the prefix is byte-identical, so
iterations 2+ read it from cache (~0.1x input price). The over-limit rewrite is
a true multi-turn follow-up and reuses the same cached prefix.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from scripts.utils import parse_skill_md


def _normalize_model(model: str) -> str:
    """Strip Claude Code-only suffixes from a session model id.

    SKILL.md tells the caller to pass `<model-id-powering-this-session>`, which
    in Claude Code can carry a `[1m]` context-window suffix (e.g.
    `claude-fable-5[1m]`). The API rejects that form — strip any `[...]` tail.
    """
    return re.sub(r"\[[^\]]*\]$", "", model)


def _get_client():
    """Lazy import + construct so --help and tests work without the SDK installed."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic SDK not installed — run: pip install -r requirements-dev.txt"
        )
    return anthropic.Anthropic()


def _extract_text(response) -> str:
    return "".join(b.text for b in response.content if b.type == "text")


def _parse_description(text: str) -> str:
    match = re.search(r"<new_description>(.*?)</new_description>", text, re.DOTALL)
    return match.group(1).strip().strip('"') if match else text.strip().strip('"')


def _build_system(skill_name: str, skill_content: str) -> list[dict]:
    """Stable prefix: instructions + skill body. Breakpoint on the last block
    caches both. Per-iteration data must NOT go here (would bust the cache)."""
    instructions = f"""You are optimizing a skill description for a Claude Code skill called "{skill_name}". A "skill" is sort of like a prompt, but with progressive disclosure -- there's a title and description that Claude sees when deciding whether to use the skill, and then if it does use the skill, it reads the .md file which has lots more details and potentially links to other resources in the skill folder like helper files and scripts and additional documentation or examples.

The description appears in Claude's "available_skills" list. When a user sends a query, Claude decides whether to invoke the skill based solely on the title and on this description. Your goal is to write a description that triggers for relevant queries, and doesn't trigger for irrelevant ones.

When given eval failures, generalize from them to broader categories of user intent — do NOT produce an ever-expanding list of specific queries. The reason is twofold:

1. Avoid overfitting
2. The list might get loooong and it's injected into ALL queries and there might be a lot of skills, so we don't want to blow too much space on any given description.

Concretely, your description should not be more than about 100-200 words, even if that comes at the cost of accuracy. There is a hard limit of 1024 characters — descriptions over that will be truncated, so stay comfortably under it.

Here are some tips that we've found to work well in writing these descriptions:
- The skill should be phrased in the imperative -- "Use this skill for" rather than "this skill does"
- The skill description should focus on the user's intent, what they are trying to achieve, vs. the implementation details of how the skill works.
- The description competes with other skills for Claude's attention — make it distinctive and immediately recognizable.
- If you're getting lots of failures after repeated attempts, change things up. Try different sentence structures or wordings.

I'd encourage you to be creative and mix up the style in different iterations since you'll have multiple opportunities to try different approaches and we'll just grab the highest-scoring one at the end.

Always respond with only the new description text in <new_description> tags, nothing else."""

    return [
        {"type": "text", "text": instructions},
        {
            "type": "text",
            "text": f"Skill content (for context on what the skill does):\n<skill_content>\n{skill_content}\n</skill_content>",
            "cache_control": {"type": "ephemeral"},
        },
    ]


def improve_description(
    skill_name: str,
    skill_content: str,
    current_description: str,
    eval_results: dict,
    history: list[dict],
    model: str,
    test_results: dict | None = None,
    log_dir: Path | None = None,
    iteration: int | None = None,
) -> str:
    """Call Claude to improve the description based on eval results."""
    failed_triggers = [
        r for r in eval_results["results"]
        if r["should_trigger"] and not r["pass"]
    ]
    false_triggers = [
        r for r in eval_results["results"]
        if not r["should_trigger"] and not r["pass"]
    ]

    # Build scores summary
    train_score = f"{eval_results['summary']['passed']}/{eval_results['summary']['total']}"
    if test_results:
        test_score = f"{test_results['summary']['passed']}/{test_results['summary']['total']}"
        scores_summary = f"Train: {train_score}, Test: {test_score}"
    else:
        scores_summary = f"Train: {train_score}"

    # Per-iteration (volatile) data — user turn, after the cached prefix
    prompt = f"""Here's the current description:
<current_description>
"{current_description}"
</current_description>

Current scores ({scores_summary}):
<scores_summary>
"""
    if failed_triggers:
        prompt += "FAILED TO TRIGGER (should have triggered but didn't):\n"
        for r in failed_triggers:
            prompt += f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
        prompt += "\n"

    if false_triggers:
        prompt += "FALSE TRIGGERS (triggered but shouldn't have):\n"
        for r in false_triggers:
            prompt += f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
        prompt += "\n"

    if history:
        prompt += "PREVIOUS ATTEMPTS (do NOT repeat these — try something structurally different):\n\n"
        for h in history:
            train_s = f"{h.get('train_passed', h.get('passed', 0))}/{h.get('train_total', h.get('total', 0))}"
            test_s = f"{h.get('test_passed', '?')}/{h.get('test_total', '?')}" if h.get('test_passed') is not None else None
            score_str = f"train={train_s}" + (f", test={test_s}" if test_s else "")
            prompt += f'<attempt {score_str}>\n'
            prompt += f'Description: "{h["description"]}"\n'
            if "results" in h:
                prompt += "Train results:\n"
                for r in h["results"]:
                    status = "PASS" if r["pass"] else "FAIL"
                    prompt += f'  [{status}] "{r["query"][:80]}" (triggered {r["triggers"]}/{r["runs"]})\n'
            if h.get("note"):
                prompt += f'Note: {h["note"]}\n'
            prompt += "</attempt>\n\n"

    prompt += """</scores_summary>

Based on the failures, write a new and improved description that is more likely to trigger correctly. Respond with only the new description in <new_description> tags."""

    client = _get_client()
    api_model = _normalize_model(model)
    system = _build_system(skill_name, skill_content)
    messages = [{"role": "user", "content": prompt}]

    response = client.messages.create(
        model=api_model,
        max_tokens=4096,
        system=system,
        messages=messages,
    )
    text = _extract_text(response)
    description = _parse_description(text)

    transcript: dict = {
        "iteration": iteration,
        "prompt": prompt,
        "response": text,
        "parsed_description": description,
        "char_count": len(description),
        "over_limit": len(description) > 1024,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cache_creation_input_tokens": response.usage.cache_creation_input_tokens,
            "cache_read_input_tokens": response.usage.cache_read_input_tokens,
        },
    }

    # Safety net: the prompt already states the 1024-char hard limit, but if
    # the model blew past it anyway, do a true multi-turn follow-up (the
    # cached system prefix is reused; pre-migration `claude -p` was one-shot
    # and had to re-inline everything).
    if len(description) > 1024:
        shorten_prompt = (
            f"That description is {len(description)} characters, over the "
            f"1024-character hard limit. Rewrite it to be under 1024 characters "
            f"while keeping the most important trigger words and intent "
            f"coverage. Respond with only the new description in "
            f"<new_description> tags."
        )
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": shorten_prompt})
        shorten_response = client.messages.create(
            model=api_model,
            max_tokens=4096,
            system=system,
            messages=messages,
        )
        shorten_text = _extract_text(shorten_response)
        shortened = _parse_description(shorten_text)

        transcript["rewrite_prompt"] = shorten_prompt
        transcript["rewrite_response"] = shorten_text
        transcript["rewrite_description"] = shortened
        transcript["rewrite_char_count"] = len(shortened)
        transcript["rewrite_usage"] = {
            "input_tokens": shorten_response.usage.input_tokens,
            "cache_read_input_tokens": shorten_response.usage.cache_read_input_tokens,
        }
        description = shortened

    transcript["final_description"] = description

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"improve_iter_{iteration or 'unknown'}.json"
        log_file.write_text(json.dumps(transcript, indent=2))

    return description


def main():
    parser = argparse.ArgumentParser(description="Improve a skill description based on eval results")
    parser.add_argument("--eval-results", required=True, help="Path to eval results JSON (from run_eval.py)")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--history", default=None, help="Path to history JSON (previous attempts)")
    parser.add_argument("--model", required=True, help="Model for improvement (API model id; Claude Code [1m] suffix is stripped)")
    parser.add_argument("--verbose", action="store_true", help="Print thinking to stderr")
    args = parser.parse_args()

    skill_path = Path(args.skill_path)
    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    eval_results = json.loads(Path(args.eval_results).read_text())
    history = []
    if args.history:
        history = json.loads(Path(args.history).read_text())

    name, _, content = parse_skill_md(skill_path)
    current_description = eval_results["description"]

    if args.verbose:
        print(f"Current: {current_description}", file=sys.stderr)
        print(f"Score: {eval_results['summary']['passed']}/{eval_results['summary']['total']}", file=sys.stderr)

    new_description = improve_description(
        skill_name=name,
        skill_content=content,
        current_description=current_description,
        eval_results=eval_results,
        history=history,
        model=args.model,
    )

    if args.verbose:
        print(f"Improved: {new_description}", file=sys.stderr)

    # Output as JSON with both the new description and updated history
    output = {
        "description": new_description,
        "history": history + [{
            "description": current_description,
            "passed": eval_results["summary"]["passed"],
            "failed": eval_results["summary"]["failed"],
            "total": eval_results["summary"]["total"],
            "results": eval_results["results"],
        }],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
