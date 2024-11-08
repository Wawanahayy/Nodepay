class Account:
    def __init__(self, email, password, uid, access_token, user_agent, proxy_url):
        self.email = email
        self.password = password
        self.uid = uid
        self.access_token = access_token
        self.user_agent = user_agent
        self.proxy_url = proxy_url

    def __repr__(self):
        return f"[{self.email}]"
