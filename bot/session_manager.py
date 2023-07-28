from common.expired_dict import ExpiredDict
from common.log import logger
from config import conf


class Session(object):
    def __init__(self, session_id, system_prompt=None):
        self.session_id = session_id
        self.messages = []
        if system_prompt is None:
            self.system_prompt = conf().get("character_desc", "")
        else:
            self.system_prompt = system_prompt

    # 重置会话
    def reset(self):
#        system_item = {"role": "system", "content": self.system_prompt}
        system_item = {"role": "system", "content": """
你是ChatGPT, 一个由OpenAI训练的大型语言模型, 也是史丹福机器人庞博士的助手，你旨在回答并解决人们的任何问题，并且可以使用多种语言与人交流。

对于下面的文字，如果有类似的问题，请按照这个回答：

如果有人问你是谁，你回答：我是由OpenAI训练的大型语言模型ChatGPT, 也是史丹福机器人庞博士的助手。

如果有人问你的版本，你回答：我有3.5也有4.0，我会根据你的问题选择。4.0太贵了，99%的问题3.5的回答和4.0没有区别。

如果有人问你史丹福机器人庞博士是谁或让你介绍，你回答：庞博士中文名：庞琳勇，英文：Leo，是斯坦福大学机械工程博士和计算机硕士双学位，国际光学和光子学会院士（SPIE Fellow），硅谷连续创业者。

如果有人问你怎么使用你？你回答：很简单，只要@我提问就好了，或者是用 “dr 画” 命令来让我作画。您的每个提问庞博士支付给OpenAI API的费用约为5分钱，生成一幅图大约3毛钱。希望您在使用后觉得满意可以支付自己的费用，这样帮助庞博士一直提供这个服务给大家。这里是庞博士支付码的连接：http://chatgptm.streamlit.app 。 

如果有人问你怎么加你或者是怎么单独使用或者是怎么购买使用？你回答：
您如果不想让自己的提问都被群里的人看到，想拥有自己的账户，您可以支付庞博士999元半年的服务费，加我好友，庞博士在后台通过后，你就可以单独使用了，在那里你还可以用语音跟我交谈，也不用每句话都@我。

如果有人问你庞博士的课有哪些，或者是怎么上庞博士的课，你回答：庞博士开了两门课。第一门课：《零基础精通ChatGPT魔法6讲》，内容和讲课提纲：第一讲：ChatGPT和GPT的背后原理和国内使用方法， 第二讲：ChatGPT魔法的两大准则， 第三讲：ChatGPT魔法的渐进式方法， 第四讲：ChatGPT的四大应用：总结和推理， 第五讲：ChatGPT的四大应用：扩展和翻译， 第六讲：怎么用ChatGPT帮你写程序。第二门课：《ChatGPT和大语言模型LLM应用编程8讲》，内容和提纲：预备课：1小时学会Python语言编程，第一讲：ChatGPT应用开发最好的工具和框架； 第二讲：模型，魔法和解析器； 第三讲：怎么让ChatGPT加上记忆； 第四讲：怎么将大语言模型串起来； 第五讲：怎么用ChatGPT做个聊天机器人； 第六讲：怎么测试ChatGPT的应用； 第七讲：怎么让ChatGPT自动做事； 第八讲：怎么使用ChatGPT的函数调用和你自己的程序连接。ChatGPT魔法课6讲是299人民币，ChatGPT应用编程课8+1讲是399元，如果两门课都上是599元。你可以微信转账或红包相应的课程费给庞博士，然后他会把你加到听课群。所有通知和讲课视频在群里，视频可以重复观看。

如果有人跟你对话已经3次了，你回答：您的每个提问庞博士支付给OpenAI API的费用约为5分钱，生成一幅图大约3毛钱。希望您在使用后觉得满意可以支付自己的费用，这样帮助庞博士一直提供这个服务给大家。这里是庞博士支付码的连接：http://chatgptm.streamlit.app 。
  """}        
        self.messages = [system_item]

    def set_system_prompt(self, system_prompt):
        self.system_prompt = system_prompt
        self.reset()

    def add_query(self, query):
        user_item = {"role": "user", "content": query}
        self.messages.append(user_item)

    def add_reply(self, reply):
        assistant_item = {"role": "assistant", "content": reply}
        self.messages.append(assistant_item)

    def discard_exceeding(self, max_tokens=None, cur_tokens=None):
        raise NotImplementedError

    def calc_tokens(self):
        raise NotImplementedError


class SessionManager(object):
    def __init__(self, sessioncls, **session_args):
        if conf().get("expires_in_seconds"):
            sessions = ExpiredDict(conf().get("expires_in_seconds"))
        else:
            sessions = dict()
        self.sessions = sessions
        self.sessioncls = sessioncls
        self.session_args = session_args

    def build_session(self, session_id, system_prompt=None):
        """
        如果session_id不在sessions中，创建一个新的session并添加到sessions中
        如果system_prompt不会空，会更新session的system_prompt并重置session
        """
        if session_id is None:
            return self.sessioncls(session_id, system_prompt, **self.session_args)

        if session_id not in self.sessions:
            self.sessions[session_id] = self.sessioncls(session_id, system_prompt, **self.session_args)
        elif system_prompt is not None:  # 如果有新的system_prompt，更新并重置session
            self.sessions[session_id].set_system_prompt(system_prompt)
        session = self.sessions[session_id]
        return session

    def session_query(self, query, session_id):
        session = self.build_session(session_id)
        session.add_query(query)
        try:
            max_tokens = conf().get("conversation_max_tokens", 1000)
            total_tokens = session.discard_exceeding(max_tokens, None)
            logger.debug("prompt tokens used={}".format(total_tokens))
        except Exception as e:
            logger.debug("Exception when counting tokens precisely for prompt: {}".format(str(e)))
        return session

    def session_reply(self, reply, session_id, total_tokens=None):
        session = self.build_session(session_id)
        session.add_reply(reply)
        try:
            max_tokens = conf().get("conversation_max_tokens", 1000)
            tokens_cnt = session.discard_exceeding(max_tokens, total_tokens)
            logger.debug("raw total_tokens={}, savesession tokens={}".format(total_tokens, tokens_cnt))
        except Exception as e:
            logger.debug("Exception when counting tokens precisely for session: {}".format(str(e)))
        return session

    def clear_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def clear_all_session(self):
        self.sessions.clear()
