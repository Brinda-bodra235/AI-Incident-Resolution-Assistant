import re

class LogParser:
    @staticmethod
    def parse(raw_log: str) -> str:
        lines = [line.strip() for line in raw_log.strip().split("\n") if line.strip()]
        if not lines:
            return "Empty Log"
        
        # 1. Extract timestamps
        timestamp_match = re.search(r'\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?\b', raw_log)
        timestamp = timestamp_match.group(0) if timestamp_match else "Unknown Time"

        # 2. Extract severity/level
        level_match = re.search(r'\b(ERROR|CRITICAL|WARNING|SEVERE)\b', raw_log, re.IGNORECASE)
        level = level_match.group(1).upper() if level_match else "UNKNOWN LEVEL"

        # 3. Extract Error type / Exception class
        error_type_match = re.search(r'\b([a-zA-Z_0-9]*Error|[a-zA-Z_0-9]*Exception)\b', raw_log)
        error_type = error_type_match.group(1) if error_type_match else None

        if not error_type:
            # Fallback checks
            for keyword in ["timeout", "connection", "auth", "permission", "disk full", "out of memory"]:
                if keyword in raw_log.lower():
                    error_type = f"{keyword.title()} Issue"
                    break
        if not error_type:
            error_type = "Generic Application Issue"

        # 4. Extract message & stack trace
        stack_trace_lines = []
        message_lines = []
        in_stack_trace = False
        
        for line in lines:
            if "traceback" in line.lower() or line.lower().startswith("at "):
                in_stack_trace = True
            if in_stack_trace:
                stack_trace_lines.append(line)
            else:
                message_lines.append(line)
        
        message = " | ".join(message_lines[:3])
        if len(message) > 200:
            message = message[:200] + "..."

        stack_trace_str = "\n".join(stack_trace_lines[:10])
        if len(stack_trace_lines) > 10:
            stack_trace_str += "\n... (truncated)"

        summary = f"[{level}] {error_type} at {timestamp}\nMessage: {message}"
        if stack_trace_str:
            summary += f"\nStack Trace:\n{stack_trace_str}"
            
        return summary
