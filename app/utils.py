def parse_error(e: Exception) -> None:
    return f"ErrorType : {type(e).__name__}, Error : {e}"
