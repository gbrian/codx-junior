import logging
import datetime
import jwt

from codx.junior.settings import read_global_settings
from codx.junior.model.model import CodxUser, CodxUserLogin


logger = logging.getLogger(__name__)


class UserSecurityManager():
    def __init__(self):
        self.global_settings = read_global_settings()
    
    def find_user(self, username: str,  email: str):
        return next((user for user in self.global_settings.users
            if user.username == username or user.email == email), None)

    def login_user(self, user: CodxUserLogin = None, token: str = None) -> CodxUser:
        if token:
            decoded = jwt.decode(token, self.global_settings.secret, algorithms=["HS256"])
            user = CodxUserLogin(**decoded)
        user = self.find_user(username=user.username, email=user.email)
        if user:
            user.token = jwt.encode({"email": user.email}, self.global_settings.secret, algorithm="HS256")
        return user