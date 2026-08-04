class DocumentProcessingService:
    def __init__(
        self,
        repository: DocumentRepository,
        storage: StorageService,
        parser: ParserService,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
    ):
        self.repository = repository
        self.storage = storage
        self.parser = parser
        self.chunking_service = chunking_service
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def process(self, document_id: UUID) -> None:
        document = self.repository.get_by_id(document_id)

        if document is None:
            logger.warning(
                "Document %s not found. Skipping processing.",
                document_id,
            )
            return

        claimed = self.repository.claim_for_processing(document.id)

        if not claimed:
            logger.info("Document is already being processed.")
            return

        file_stream = self.storage.retrieve(document.storage_key)
