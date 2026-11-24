class AttemptError(Exception):
    def __init__(self, status, detail, **extra):
        super().__init__(detail)
        self.status = status
        self.body = {"detail": detail, **extra}
