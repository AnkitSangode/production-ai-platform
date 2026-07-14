class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        storage: StorageService,
        db: Session,
    ):
        self.repository = repository
        self.storage = storage
        self.db = db

    def upload_document(self,file: UploadFile,current_user: User,):
        pass