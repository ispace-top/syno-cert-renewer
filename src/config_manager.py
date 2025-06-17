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
        value = default
        
        # 1. 首先从文件配置中查找
        temp_config = self.config
        try:
            keys = key_path.split('.')
            for key in keys:
                if isinstance(temp_config, dict):
                    temp_config = temp_config.get(key)
                else:
                    temp_config = None
                    break
            if temp_config is not None:
                value = temp_config
        except (KeyError, TypeError):
            pass  # 未找到，将使用默认值或环境变量

        # 2. 检查环境变量是否有更高优先级
        env_value = None
        if env_var:
            env_value = os.environ.get(env_var)

        if env_value is not None:
            value = env_value
            
        return value

