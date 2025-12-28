import json
import os
from typing import Any, Dict, Optional

TOKEN_FILE = "./data/token.json"


def load_tokens() -> Dict[str, Any]:
    """加载所有 token 配置"""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    initial_tokens = {
        "bohe_sign_token": "",
        "linux_do_connect_token": "",
        "linux_do_token": "",
        "newapi_session": "",
        "newapi_user_id": ""
    }
    try:
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(initial_tokens, f, indent=4, ensure_ascii=False)
        return initial_tokens
    except Exception:
        pass
    return {}


def save_tokens(bohe_token: Optional[str] = None,
                linux_do_connect_token: Optional[str] = None,
                linux_do_token: Optional[str] = None,
                newapi_session: Optional[str] = None,
                newapi_user_id: Optional[str] = None) -> None:
    """保存 token 配置"""
    tokens = load_tokens()
    
    if bohe_token is not None:
        tokens["bohe_sign_token"] = bohe_token
    if linux_do_connect_token is not None:
        tokens["linux_do_connect_token"] = linux_do_connect_token
    if linux_do_token is not None:
        tokens["linux_do_token"] = linux_do_token
    if newapi_session is not None:
        tokens["newapi_session"] = newapi_session
    if newapi_user_id is not None:
        tokens["newapi_user_id"] = newapi_user_id

    try:
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving tokens: {e}")


def get_token(key: str) -> Optional[str]:
    """获取指定的 token 值"""
    tokens = load_tokens()
    return tokens.get(key)


def save_newapi_config(session: str, user_id: str) -> bool:
    """保存 NewAPI 配置"""
    try:
        save_tokens(newapi_session=session, newapi_user_id=user_id)
        return True
    except Exception:
        return False


def get_newapi_config() -> Dict[str, str]:
    """获取 NewAPI 配置"""
    tokens = load_tokens()
    return {
        "session": tokens.get("newapi_session", ""),
        "user_id": tokens.get("newapi_user_id", "")
    }