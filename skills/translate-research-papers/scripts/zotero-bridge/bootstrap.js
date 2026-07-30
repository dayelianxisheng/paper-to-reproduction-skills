var PDF2zhBridge = {
  version: "0.1.1",
  token: null,
  tokenPath: null,
  endpointPaths: [
    "/pdf2zh-bridge/update",
    "/pdf2zh-bridge/health",
    "/pdf2zh-bridge/archive"
  ],
  allowedImportRoot: String.raw`D:\resource\env\fanyi\server\server\translated`,

  json(status, value) {
    return [
      status,
      "application/json; charset=utf-8",
      JSON.stringify(value)
    ];
  },

  error(status, code, message) {
    return this.json(status, {
      status: "error",
      code,
      message
    });
  },

  isAuthorized(requestData) {
    let provided = requestData.headers["x-pdf2zh-bridge-token"];
    return typeof provided === "string"
      && provided.length === this.token.length
      && provided === this.token;
  },

  requireAuthorized(requestData) {
    if (!this.isAuthorized(requestData)) {
      throw Object.assign(new Error("Unauthorized"), {
        bridgeStatus: 401,
        bridgeCode: "UNAUTHORIZED"
      });
    }
  },

  getInteger(value, name, required = true) {
    if ((value === undefined || value === null || value === "") && !required) {
      return null;
    }
    let parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      throw Object.assign(new Error(`Invalid ${name}`), {
        bridgeStatus: 400,
        bridgeCode: "INVALID_ARGUMENT"
      });
    }
    return parsed;
  },

  getAllowedPDF(path) {
    if (typeof path !== "string" || !path.toLowerCase().endsWith(".pdf")) {
      throw Object.assign(new Error("translatedPath must be an absolute PDF path"), {
        bridgeStatus: 400,
        bridgeCode: "INVALID_PDF_PATH"
      });
    }

    let file;
    let root;
    try {
      file = Zotero.File.pathToFile(path);
      root = Zotero.File.pathToFile(this.allowedImportRoot);
    }
    catch (e) {
      throw Object.assign(new Error("translatedPath is not a valid Windows path"), {
        bridgeStatus: 400,
        bridgeCode: "INVALID_PDF_PATH"
      });
    }

    let filePath = file.path.toLowerCase();
    let rootPath = root.path.replace(/[\\\/]+$/, "").toLowerCase();
    if (!filePath.startsWith(rootPath + "\\")) {
      throw Object.assign(new Error("translatedPath is outside the allowed PDF2zh output directory"), {
        bridgeStatus: 403,
        bridgeCode: "PATH_NOT_ALLOWED"
      });
    }
    if (!file.exists() || !file.isFile() || file.fileSize < 5) {
      throw Object.assign(new Error("Translated PDF does not exist or is empty"), {
        bridgeStatus: 404,
        bridgeCode: "PDF_NOT_FOUND"
      });
    }
    return file;
  },

  getCollection(collectionID, libraryID) {
    let collection = Zotero.Collections.get(collectionID);
    if (!collection || collection.deleted) {
      throw Object.assign(new Error("Target collection was not found"), {
        bridgeStatus: 404,
        bridgeCode: "COLLECTION_NOT_FOUND"
      });
    }
    if (collection.libraryID !== libraryID) {
      throw Object.assign(new Error("Target collection is in a different library"), {
        bridgeStatus: 400,
        bridgeCode: "LIBRARY_MISMATCH"
      });
    }
    return collection;
  },

  copyMetadata(parent, template, metadata) {
    let fields = [
      "title",
      "shortTitle",
      "date",
      "DOI",
      "proceedingsTitle",
      "url",
      "pages",
      "language",
      "abstractNote"
    ];

    if (template) {
      for (let field of fields) {
        let value = template.getField(field);
        if (value) {
          parent.setField(field, value);
        }
      }
      parent.setCreators(template.getCreators());
    }

    metadata = metadata || {};
    for (let field of fields) {
      if (typeof metadata[field] === "string" && metadata[field].trim()) {
        parent.setField(field, metadata[field].trim());
      }
    }
    if (Array.isArray(metadata.creators)) {
      parent.setCreators(metadata.creators);
    }
  },

  async archive(requestData) {
    this.requireAuthorized(requestData);
    let data = requestData.data || {};

    let sourceAttachmentID = this.getInteger(
      data.sourceAttachmentID,
      "sourceAttachmentID"
    );
    let targetCollectionID = this.getInteger(
      data.targetCollectionID,
      "targetCollectionID"
    );
    let templateItemID = this.getInteger(
      data.templateItemID,
      "templateItemID",
      false
    );
    let shortTitle = typeof data.shortTitle === "string"
      ? data.shortTitle.trim()
      : "";
    let service = typeof data.service === "string" && data.service.trim()
      ? data.service.trim()
      : "siliconflowfree";
    if (!shortTitle) {
      throw Object.assign(new Error("shortTitle is required"), {
        bridgeStatus: 400,
        bridgeCode: "INVALID_ARGUMENT"
      });
    }

    let source = await Zotero.Items.getAsync(sourceAttachmentID);
    if (!source || source.deleted || !source.isAttachment()) {
      throw Object.assign(new Error("Source attachment was not found"), {
        bridgeStatus: 404,
        bridgeCode: "SOURCE_NOT_FOUND"
      });
    }
    if (source.attachmentContentType !== "application/pdf") {
      throw Object.assign(new Error("Source attachment is not a PDF"), {
        bridgeStatus: 400,
        bridgeCode: "SOURCE_NOT_PDF"
      });
    }

    let targetCollection = this.getCollection(
      targetCollectionID,
      source.libraryID
    );
    let translatedFile = this.getAllowedPDF(data.translatedPath);
    let sourcePath = source.getFilePath();
    if (sourcePath && sourcePath.toLowerCase() === translatedFile.path.toLowerCase()) {
      throw Object.assign(new Error("Translated PDF and source PDF are the same file"), {
        bridgeStatus: 400,
        bridgeCode: "SAME_FILE"
      });
    }

    let template = null;
    if (templateItemID) {
      template = await Zotero.Items.getAsync(templateItemID);
      if (!template || template.deleted || !template.isRegularItem()) {
        throw Object.assign(new Error("Template bibliographic item was not found"), {
          bridgeStatus: 404,
          bridgeCode: "TEMPLATE_NOT_FOUND"
        });
      }
      if (template.libraryID !== source.libraryID) {
        throw Object.assign(new Error("Template item is in a different library"), {
          bridgeStatus: 400,
          bridgeCode: "LIBRARY_MISMATCH"
        });
      }
    }

    let parent = source.parentItemID
      ? await Zotero.Items.getAsync(source.parentItemID)
      : null;
    let parentCreated = false;

    if (!parent) {
      let itemType = typeof data.itemType === "string" && data.itemType
        ? data.itemType
        : "conferencePaper";
      if (!Zotero.ItemTypes.getID(itemType)) {
        throw Object.assign(new Error("Unsupported bibliographic item type"), {
          bridgeStatus: 400,
          bridgeCode: "INVALID_ITEM_TYPE"
        });
      }

      parent = new Zotero.Item(itemType);
      parent.libraryID = source.libraryID;
      this.copyMetadata(parent, template, data.metadata);
      if (!parent.getField("title")) {
        parent.setField(
          "title",
          source.getField("title") || shortTitle
        );
      }
      if (!parent.getField("shortTitle")) {
        parent.setField("shortTitle", shortTitle);
      }
      parent.addToCollection(targetCollection.id);
      await parent.saveTx();
      parentCreated = true;
    }
    else {
      if (!parent.isRegularItem()) {
        throw Object.assign(new Error("Existing source parent is not a bibliographic item"), {
          bridgeStatus: 409,
          bridgeCode: "INVALID_EXISTING_PARENT"
        });
      }
      if (!parent.getCollections().includes(targetCollection.id)) {
        parent.addToCollection(targetCollection.id);
        await parent.saveTx();
      }
    }

    let originalTitle = `${shortTitle}-original`;
    let sourceChanged = false;
    if (source.parentItemID !== parent.id) {
      source.parentItemID = parent.id;
      sourceChanged = true;
    }
    if (source.getField("title") !== originalTitle) {
      source.setField("title", originalTitle);
      sourceChanged = true;
    }
    for (let collectionID of source.getCollections()) {
      source.removeFromCollection(collectionID);
      sourceChanged = true;
    }
    if (sourceChanged) {
      await source.saveTx();
    }

    let translatedTitle = `${shortTitle}-${service}-compare`;
    let translated = parent.getAttachments()
      .map(id => Zotero.Items.get(id))
      .find(item => item && !item.deleted && item.getField("title") === translatedTitle);
    let attachmentCreated = false;

    if (!translated) {
      translated = await Zotero.Attachments.importFromFile({
        file: translatedFile.path,
        parentItemID: parent.id,
        libraryID: source.libraryID,
        title: translatedTitle
      });
      attachmentCreated = true;
    }

    return {
      status: "ok",
      idempotent: !parentCreated && !attachmentCreated && !sourceChanged,
      targetCollection: {
        id: targetCollection.id,
        key: targetCollection.key,
        name: targetCollection.name
      },
      parent: {
        id: parent.id,
        key: parent.key,
        title: parent.getField("title"),
        collections: parent.getCollections(),
        created: parentCreated
      },
      original: {
        id: source.id,
        key: source.key,
        title: source.getField("title"),
        parentItemID: source.parentItemID,
        collections: source.getCollections(),
        path: source.getFilePath()
      },
      translated: {
        id: translated.id,
        key: translated.key,
        title: translated.getField("title"),
        parentItemID: translated.parentItemID,
        collections: translated.getCollections(),
        path: translated.getFilePath(),
        created: attachmentCreated
      }
    };
  },

  async loadOrCreateToken() {
    this.tokenPath = PathUtils.join(
      Zotero.DataDirectory.dir,
      "pdf2zh-bridge.token"
    );
    let token = "";
    try {
      token = (await Zotero.File.getContentsAsync(this.tokenPath)).trim();
    }
    catch (e) {
      if (await IOUtils.exists(this.tokenPath)) {
        throw e;
      }
    }

    if (!/^[A-Za-z0-9]{48,128}$/.test(token)) {
      token = (
        Services.uuid.generateUUID().toString()
        + Services.uuid.generateUUID().toString()
      ).replace(/[{}-]/g, "");
      await Zotero.File.putContentsAsync(
        this.tokenPath,
        token + "\n",
        "UTF-8"
      );
    }
    this.token = token;
  },

  async register() {
    await this.loadOrCreateToken();
    let bridge = this;

    class UpdateEndpoint {
      supportedMethods = ["GET"];

      async init() {
        return bridge.json(200, {
          addons: {
            "pdf2zh-bridge@codex.local": {
              updates: []
            }
          }
        });
      }
    }

    class HealthEndpoint {
      supportedMethods = ["GET"];

      async init(requestData) {
        try {
          bridge.requireAuthorized(requestData);
          return bridge.json(200, {
            status: "ok",
            bridgeVersion: bridge.version,
            zoteroVersion: Zotero.version,
            tokenPath: bridge.tokenPath,
            allowedImportRoot: bridge.allowedImportRoot
          });
        }
        catch (e) {
          return bridge.error(
            e.bridgeStatus || 500,
            e.bridgeCode || "INTERNAL_ERROR",
            e.message || "Internal error"
          );
        }
      }
    }

    class ArchiveEndpoint {
      supportedMethods = ["POST"];
      supportedDataTypes = ["application/json"];

      async init(requestData) {
        try {
          let result = await bridge.archive(requestData);
          return bridge.json(200, result);
        }
        catch (e) {
          Zotero.logError(e);
          return bridge.error(
            e.bridgeStatus || 500,
            e.bridgeCode || "INTERNAL_ERROR",
            e.message || "Internal error"
          );
        }
      }
    }

    Zotero.Server.Endpoints["/pdf2zh-bridge/update"] = UpdateEndpoint;
    Zotero.Server.Endpoints["/pdf2zh-bridge/health"] = HealthEndpoint;
    Zotero.Server.Endpoints["/pdf2zh-bridge/archive"] = ArchiveEndpoint;
    Zotero.debug("PDF2zh Local Bridge registered");
  },

  unregister() {
    for (let path of this.endpointPaths) {
      delete Zotero.Server.Endpoints[path];
    }
    this.token = null;
  }
};

function install(data, reason) {}

async function startup(data, reason) {
  await Zotero.initializationPromise;
  await PDF2zhBridge.register();
}

function shutdown(data, reason) {
  if (typeof Zotero !== "undefined" && Zotero.Server) {
    PDF2zhBridge.unregister();
  }
}

function uninstall(data, reason) {}
