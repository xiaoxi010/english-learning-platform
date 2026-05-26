# ai_correct.py - AI 批改基础词汇
import requests
import json

class AICorrector:
    def __init__(self):
        self.api_key = "sk-bxzpohrekmomlrmyzislhqukvoyrbllhlqvfvrcqtixwokei"
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.model_name = "deepseek-ai/DeepSeek-V3"
    
    def correct_batch(self, words_data):
        """
        批量批改基础词汇
        words_data: [{'word': 'apple', 'correct_meaning': '苹果', 'user_answer': '苹果'}, ...]
        返回: {'scores': [1.0, 0.75, ...], 'used_ai': True}
        """
        try:
            prompt = self._build_prompt(words_data)
            
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": "你是一个英语单词批改助手。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                scores = self._parse_response(result, len(words_data))
                if scores:
                    return {'scores': scores, 'used_ai': True, 'success': True}
                else:
                    return {'scores': None, 'used_ai': False, 'success': False, 'error': '解析AI响应失败'}
            else:
                return {'scores': None, 'used_ai': False, 'success': False, 'error': f'API返回{response.status_code}'}
                
        except requests.Timeout:
            return {'scores': None, 'used_ai': False, 'success': False, 'error': 'AI批改超时'}
        except Exception as e:
            return {'scores': None, 'used_ai': False, 'success': False, 'error': str(e)}
    
    def _build_prompt(self, words_data):
        items = []
        for i, w in enumerate(words_data):
            items.append(f"{i+1}. 单词: {w['word']}, 正确答案: {w['correct_meaning']}, 用户答案: {w['user_answer']}")
        
        prompt = f"""请批改以下{len(words_data)}个英语单词的汉译答案。

评分规则：
第一步：查询每个英文单词的所有常见汉译（包括不同语境下的翻译）。
第二步：判断用户答案是否匹配任何一个常见汉译（包括同义词、近义词、相似表达）：
  - 如果用户答案的意思在常见汉译中能找到 → 给 1.0 分
第三步：如果不在常见汉译中，判断用户答案与正确含义的语义关联程度：
  - 强关联（意思接近但表达不准确）→ 0.75 分
  - 中等关联（部分相关）→ 0.5 分
  - 弱关联（只有一点点关系）→ 0.25 分
  - 完全无关或未作答 → 0 分

{chr(10).join(items)}

请只返回JSON数组格式，不要其他文字：
[分数1, 分数2, ...]"""
        return prompt
    
    def _parse_response(self, result, expected_count):
        try:
            content = result['choices'][0]['message']['content'].strip()
            if '[' in content and ']' in content:
                start = content.index('[')
                end = content.index(']') + 1
                scores = json.loads(content[start:end])
                valid_scores = []
                for s in scores[:expected_count]:
                    s = float(s)
                    if s > 1: s = 1.0
                    if s < 0: s = 0.0
                    valid_scores.append(round(s, 2))
                while len(valid_scores) < expected_count:
                    valid_scores.append(0.0)
                return valid_scores
        except:
            pass
        return None

ai_corrector = AICorrector()