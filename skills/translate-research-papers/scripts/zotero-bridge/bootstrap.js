var PDF2zhBridge = {
  version: "0.4.0",
  token: null,
  tokenPath: null,
  endpointPaths: [
    "/pdf2zh-bridge/update",
    "/pdf2zh-bridge/health",
    "/pdf2zh-bridge/prepare",
    "/pdf2zh-bridge/archive",
    "/pdf2zh-bridge/inventory",
    "/pdf2zh-bridge/github"
  ],
  allowedSourceRoot: null,
  allowedImportRoot: null,
  localConfigPath: null,

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

  parseLocalYAML(text) {
    let values = {};
    for (let line of text.split(/\r?\n/)) {
      line = line.trim();
      if (!line || line.startsWith("#")) {
        continue;
      }
      let match = line.match(/^([A-Za-z0-9_]+):\s*(.+)$/);
      if (!match) {
        continue;
      }
      let value = match[2].trim();
      if (value.startsWith('"')) {
        try {
          value = JSON.parse(value);
        }
        catch (e) {
          throw new Error(`Invalid YAML value for ${match[1]}`);
        }
      }
      values[match[1]] = value;
    }
    return values;
  },

  async resolveAllowedRoots() {
    let configuredSource = Services.env.get("PDF2ZH_SOURCE_DIRECTORY");
    let configuredTranslated = Services.env.get("PDF2ZH_TRANSLATED_DIRECTORY");
    this.localConfigPath = Services.env.get("PDF2ZH_SKILL_CONFIG") || null;
    if ((!configuredSource || !configuredTranslated) && this.localConfigPath) {
      let contents;
      try {
        contents = await Zotero.File.getContentsAsync(this.localConfigPath);
      }
      catch (e) {
        throw new Error("PDF2ZH_SKILL_CONFIG does not point to a readable YAML file");
      }
      let localConfig = this.parseLocalYAML(contents);
      configuredSource = configuredSource || localConfig.pdf2zh_source_directory;
      configuredTranslated = configuredTranslated
        || localConfig.pdf2zh_translated_directory;
    }
    if (!configuredSource || !configuredTranslated) {
      throw new Error(
        "Set PDF2ZH_SKILL_CONFIG or both PDF2ZH source/translated directory variables"
      );
    }
    this.allowedSourceRoot = configuredSource;
    this.allowedImportRoot = configuredTranslated;
  },

  getAllowedPDF(path, allowedRoot, pathName) {
    if (typeof path !== "string" || !path.toLowerCase().endsWith(".pdf")) {
      throw Object.assign(new Error(`${pathName} must be an absolute PDF path`), {
        bridgeStatus: 400,
        bridgeCode: "INVALID_PDF_PATH"
      });
    }

    let file;
    let root;
    try {
      file = Zotero.File.pathToFile(path);
      root = Zotero.File.pathToFile(allowedRoot);
      file.normalize();
      root.normalize();
    }
    catch (e) {
      throw Object.assign(new Error(`${pathName} is not a valid absolute path`), {
        bridgeStatus: 400,
        bridgeCode: "INVALID_PDF_PATH"
      });
    }

    let separator = Zotero.isWin ? "\\" : "/";
    let filePath = file.path;
    let rootPath = root.path.replace(/[\\\/]+$/, "");
    if (Zotero.isWin) {
      filePath = filePath.toLowerCase();
      rootPath = rootPath.toLowerCase();
    }
    if (!filePath.startsWith(rootPath + separator)) {
      throw Object.assign(new Error(`${pathName} is outside its allowed directory`), {
        bridgeStatus: 403,
        bridgeCode: "PATH_NOT_ALLOWED"
      });
    }
    if (!file.exists() || !file.isFile() || file.fileSize < 5) {
      throw Object.assign(new Error(`${pathName} does not exist or is empty`), {
        bridgeStatus: 404,
        bridgeCode: "PDF_NOT_FOUND"
      });
    }
    return file;
  },

  getAllowedSourcePDF(path) {
    return this.getAllowedPDF(path, this.allowedSourceRoot, "sourcePath");
  },

  getAllowedTranslatedPDF(path) {
    return this.getAllowedPDF(path, this.allowedImportRoot, "translatedPath");
  },

  getCollection(collectionID, libraryID) {
    let collection = Zotero.Collections.get(collectionID);
    if (!collection || collection.deleted) {
      throw Object.assign(new Error("Target collection was not found"), {
        bridgeStatus: 404,
        bridgeCode: "COLLECTION_NOT_FOUND"
      });
    }
    if (libraryID !== null && collection.libraryID !== libraryID) {
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

  findAttachmentInCollection(collection, title) {
    for (let item of collection.getChildItems()) {
      if (item.isAttachment() && item.getField("title") === title) {
        return item;
      }
      if (!item.isRegularItem()) {
        continue;
      }
      for (let attachmentID of item.getAttachments()) {
        let attachment = Zotero.Items.get(attachmentID);
        if (attachment && !attachment.deleted && attachment.getField("title") === title) {
          return attachment;
        }
      }
    }
    return null;
  },

  async prepare(requestData) {
    this.requireAuthorized(requestData);
    let data = requestData.data || {};
    let targetCollectionID = this.getInteger(
      data.targetCollectionID,
      "targetCollectionID"
    );
    let shortTitle = typeof data.shortTitle === "string"
      ? data.shortTitle.trim()
      : "";
    if (!shortTitle) {
      throw Object.assign(new Error("shortTitle is required"), {
        bridgeStatus: 400,
        bridgeCode: "INVALID_ARGUMENT"
      });
    }

    let targetCollection = this.getCollection(targetCollectionID, null);
    let sourceFile = this.getAllowedSourcePDF(data.sourcePath);
    let originalTitle = `${shortTitle}-original`;
    let source = this.findAttachmentInCollection(targetCollection, originalTitle);
    let attachmentCreated = false;

    if (!source) {
      source = await Zotero.Attachments.importFromFile({
        file: sourceFile.path,
        libraryID: targetCollection.libraryID,
        collections: [targetCollection.id],
        title: originalTitle
      });
      attachmentCreated = true;
    }
    if (source.attachmentContentType !== "application/pdf") {
      throw Object.assign(new Error("Prepared source attachment is not a PDF"), {
        bridgeStatus: 409,
        bridgeCode: "SOURCE_NOT_PDF"
      });
    }

    return {
      status: "ok",
      idempotent: !attachmentCreated,
      targetCollection: {
        id: targetCollection.id,
        key: targetCollection.key,
        name: targetCollection.name
      },
      source: {
        id: source.id,
        key: source.key,
        title: source.getField("title"),
        parentItemID: source.parentItemID,
        collections: source.getCollections(),
        path: source.getFilePath(),
        created: attachmentCreated
      }
    };
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
    let translatedFile = this.getAllowedTranslatedPDF(data.translatedPath);
    let sourcePath = source.getFilePath();
    let sourcePathForCompare = sourcePath;
    let translatedPathForCompare = translatedFile.path;
    if (Zotero.isWin) {
      sourcePathForCompare = sourcePathForCompare && sourcePathForCompare.toLowerCase();
      translatedPathForCompare = translatedPathForCompare.toLowerCase();
    }
    if (sourcePathForCompare && sourcePathForCompare === translatedPathForCompare) {
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
    let attachmentRepaired = false;

    if (translated) {
      let existingPath = translated.getFilePath();
      let existingFile = existingPath
        ? Zotero.File.pathToFile(existingPath)
        : null;
      if (!existingFile || !existingFile.exists() || !existingFile.isFile()
          || existingFile.fileSize < 5) {
        await translated.eraseTx();
        translated = null;
        attachmentRepaired = true;
      }
    }

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
      idempotent: !parentCreated && !attachmentCreated && !attachmentRepaired
        && !sourceChanged,
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
        created: attachmentCreated,
        repaired: attachmentRepaired
      }
    };
  },

  normalizeGitHubURL(value) {
    if (typeof value !== "string") {
      throw Object.assign(new Error("GitHub URL must be a string"), {
        bridgeStatus: 400,
        bridgeCode: "INVALID_GITHUB_URL"
      });
    }
    let url = value.trim().replace(/\/$/, "");
    if (!/^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(url)) {
      throw Object.assign(new Error("Only canonical GitHub repository URLs are allowed"), {
        bridgeStatus: 400,
        bridgeCode: "INVALID_GITHUB_URL"
      });
    }
    return url;
  },

  async addGitHubLinks(requestData) {
    this.requireAuthorized(requestData);
    let data = requestData.data || {};
    if (!Array.isArray(data.links) || !data.links.length || data.links.length > 200) {
      throw Object.assign(new Error("links must contain between 1 and 200 entries"), {
        bridgeStatus: 400,
        bridgeCode: "INVALID_ARGUMENT"
      });
    }

    let results = [];
    for (let entry of data.links) {
      let parentItemID = this.getInteger(entry.parentItemID, "parentItemID");
      let title = typeof entry.title === "string" ? entry.title.trim() : "";
      if (!title || title.length > 200) {
        throw Object.assign(new Error("Attachment title is required and must be at most 200 characters"), {
          bridgeStatus: 400,
          bridgeCode: "INVALID_ARGUMENT"
        });
      }
      let url = this.normalizeGitHubURL(entry.url);
      let parent = await Zotero.Items.getAsync(parentItemID);
      if (!parent || parent.deleted || !parent.isRegularItem()) {
        throw Object.assign(new Error(`Parent item ${parentItemID} was not found`), {
          bridgeStatus: 404,
          bridgeCode: "PARENT_NOT_FOUND"
        });
      }

      let attachment = parent.getAttachments()
        .map(id => Zotero.Items.get(id))
        .find(item => item && !item.deleted && item.isAttachment()
          && (item.getField("url") === url || item.getField("title") === title));
      let created = false;
      let updated = false;

      if (!attachment) {
        attachment = new Zotero.Item("attachment");
        attachment.libraryID = parent.libraryID;
        attachment.parentItemID = parent.id;
        attachment.attachmentLinkMode = Zotero.Attachments.LINK_MODE_LINKED_URL;
        attachment.setField("title", title);
        attachment.setField("url", url);
        attachment.setField("accessDate", "CURRENT_TIMESTAMP");
        await attachment.saveTx();
        created = true;
      }
      else {
        if (attachment.attachmentLinkMode !== Zotero.Attachments.LINK_MODE_LINKED_URL) {
          throw Object.assign(new Error(`Existing item named ${title} is not a linked URL attachment`), {
            bridgeStatus: 409,
            bridgeCode: "ATTACHMENT_TYPE_CONFLICT"
          });
        }
        if (attachment.getField("title") !== title) {
          attachment.setField("title", title);
          updated = true;
        }
        if (attachment.getField("url") !== url) {
          attachment.setField("url", url);
          updated = true;
        }
        if (!attachment.getField("accessDate")) {
          attachment.setField("accessDate", "CURRENT_TIMESTAMP");
          updated = true;
        }
        if (updated) {
          await attachment.saveTx();
        }
      }

      results.push({
        parent: {
          id: parent.id,
          key: parent.key,
          title: parent.getField("title")
        },
        attachment: {
          id: attachment.id,
          key: attachment.key,
          title: attachment.getField("title"),
          url: attachment.getField("url"),
          parentItemID: attachment.parentItemID,
          linkMode: attachment.attachmentLinkMode,
          created,
          updated
        },
        idempotent: !created && !updated
      });
    }

    return {
      status: "ok",
      created: results.filter(result => result.attachment.created).length,
      updated: results.filter(result => result.attachment.updated).length,
      idempotent: results.filter(result => result.idempotent).length,
      results
    };
  },

  async inventory(requestData) {
    this.requireAuthorized(requestData);
    let data = requestData.data || {};
    if (!Array.isArray(data.collectionIDs) || !data.collectionIDs.length
        || data.collectionIDs.length > 50) {
      throw Object.assign(new Error("collectionIDs must contain between 1 and 50 entries"), {
        bridgeStatus: 400,
        bridgeCode: "INVALID_ARGUMENT"
      });
    }

    let items = new Map();
    for (let value of data.collectionIDs) {
      let collectionID = this.getInteger(value, "collectionID");
      let collection = this.getCollection(collectionID, null);
      for (let item of collection.getChildItems()) {
        if (!item || item.deleted || !item.isRegularItem()) {
          continue;
        }
        let existing = items.get(item.id) || {
          id: item.id,
          key: item.key,
          title: item.getField("title"),
          shortTitle: item.getField("shortTitle"),
          collections: [],
          github: []
        };
        if (!existing.collections.includes(collection.id)) {
          existing.collections.push(collection.id);
        }
        if (!existing.github.length) {
          existing.github = item.getAttachments()
            .map(id => Zotero.Items.get(id))
            .filter(attachment => attachment && !attachment.deleted
              && attachment.isAttachment()
              && attachment.attachmentLinkMode === Zotero.Attachments.LINK_MODE_LINKED_URL
              && /^https:\/\/github\.com\//.test(attachment.getField("url")))
            .map(attachment => ({
              id: attachment.id,
              key: attachment.key,
              title: attachment.getField("title"),
              url: attachment.getField("url")
            }));
        }
        items.set(item.id, existing);
      }
    }

    return {
      status: "ok",
      count: items.size,
      items: Array.from(items.values()).sort((a, b) => a.title.localeCompare(b.title))
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
    await this.resolveAllowedRoots();
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
            localConfigPath: bridge.localConfigPath,
            allowedSourceRoot: bridge.allowedSourceRoot,
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

    class PrepareEndpoint {
      supportedMethods = ["POST"];
      supportedDataTypes = ["application/json"];

      async init(requestData) {
        try {
          let result = await bridge.prepare(requestData);
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

    class GitHubEndpoint {
      supportedMethods = ["POST"];
      supportedDataTypes = ["application/json"];

      async init(requestData) {
        try {
          let result = await bridge.addGitHubLinks(requestData);
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

    class InventoryEndpoint {
      supportedMethods = ["POST"];
      supportedDataTypes = ["application/json"];

      async init(requestData) {
        try {
          let result = await bridge.inventory(requestData);
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
    Zotero.Server.Endpoints["/pdf2zh-bridge/prepare"] = PrepareEndpoint;
    Zotero.Server.Endpoints["/pdf2zh-bridge/archive"] = ArchiveEndpoint;
    Zotero.Server.Endpoints["/pdf2zh-bridge/inventory"] = InventoryEndpoint;
    Zotero.Server.Endpoints["/pdf2zh-bridge/github"] = GitHubEndpoint;
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
