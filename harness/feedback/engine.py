import re
from harness.core.models import ShellResult, Failure, TestFeedback, Message


class FeedbackEngine:
    """Parses pytest output into structured feedback. Pure function, deterministic."""

    FAILURE_PATTERN = re.compile(
        r'FAILED\s+(\S+?)::(\w+)\s+-\s+(.+?)(?:\n|$)'
    )

    def __init__(self, test_command: str, max_retries: int):
        self._test_command = test_command
        self._max_retries = max_retries

    def parse_test_output(self, output: ShellResult) -> TestFeedback:
        combined = output.stdout + "\n" + output.stderr
        passed = output.exit_code == 0

        failures = []
        for match in self.FAILURE_PATTERN.finditer(combined):
            file_path = match.group(1)
            test_name = match.group(2)
            message = match.group(3).strip()
            line = self._extract_line(message)
            failures.append(Failure(name=test_name, message=message, file=file_path, line=line))

        raw_output = combined[:2000]

        return TestFeedback(passed=passed, failures=failures, raw_output=raw_output)

    def inject(self, feedback: TestFeedback) -> Message:
        if feedback.passed:
            return Message(role="system", content="All tests passed. Task complete.")
        failure_text = "\n".join(
            f"- {f.name}: {f.message} ({f.file}:{f.line})"
            for f in feedback.failures
        )
        return Message(
            role="system",
            content=f"Tests failed ({len(feedback.failures)} failures):\n{failure_text}\n\nFix the failing tests.",
        )

    def _extract_line(self, message: str) -> int:
        line_match = re.search(r':(\d+):', message)
        return int(line_match.group(1)) if line_match else 0
