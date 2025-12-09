import os
import json
import logging

class ConfigManager:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_path='/config/config.json'):
        if self._initialized:
            return
            
        self.config = {}
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            logging.info(f"成功从 {config_path} 加载配置文件。")
        except FileNotFoundError:
            logging.info(f"配置文件 {config_path} 未找到，将仅依赖环境变量。")
        except json.JSONDecodeError:
            logging.warning(f"无法解析配置文件 {config_path}。请检查其格式。")
        except Exception as e:
            logging.error(f"加载配置文件 {config_path} 时发生未知错误: {e}")

        self._initialized = True

    def get(self, key_path: str, env_var: str = None, default=None):
        """
        根据点分隔的路径从配置中获取值，并允许环境变量覆盖。
        环境变量具有最高优先级。

        :param key_path: 点分隔的路径，例如 'general.domain'
        :param env_var: 对应的环境变量名
        :param default: 如果都找不到，则返回此默认值
        """
        # 1. 检查环境变量(不区分大小写)
        if env_var:
            # 创建一个不区分大小写的环境变量查找
            env_vars_upper = {k.upper(): v for k, v in os.environ.items()}
            env_value = env_vars_upper.get(env_var.upper())

            if env_value is not None:
                # 转换布尔值
                if env_value.lower() in ('true', 'yes', '1'):
                    return True
                if env_value.lower() in ('false', 'no', '0'):
                    return False
                # 对于非布尔值，直接返回字符串
                return env_value

        # 2. 如果环境变量未设置，则从文件配置中查找
        temp_config = self.config
        try:
            keys = key_path.split('.')
            for key in keys:
                if isinstance(temp_config, dict):
                    temp_config = temp_config.get(key)
                else:
                    return default
            if temp_config is not None:
                return temp_config
        except (KeyError, TypeError):
            pass

        # 3. 如果都找不到，则返回默认值
        return default

