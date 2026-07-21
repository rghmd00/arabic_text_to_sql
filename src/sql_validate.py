from guardrails import Guard
from guardrails_ai.exclude_sql_predicates import ExcludeSqlPredicates


sql_ast_guardrail = ExcludeSqlPredicates(
    predicates=[
        "Drop",
        "Delete",
        "Alter",
        "Insert",
        "Update",
        "Create",
        "Attach",
        "Detach",
        "Copy",
        "Pragma",
    ],
    on_fail="exception",  # type: ignore
)

guard = Guard().use(sql_ast_guardrail)


def validate_sql(sql_query: str) -> dict:
    """
    Validates a generated SQL string against security policies.
    Returns a dict: {"is_valid": bool, "message"/"error": str}
    """
    try:
        guard.validate(sql_query)
        return {"is_valid": True, "message": "SQL passed security checks."}
    except Exception as e:
        return {"is_valid": False, "error": str(e)}