import type { StorageAdapter } from "./types";

export class OPFSAdapter implements StorageAdapter<File> {
	private directoryName: string;
	private static readonly fallbackDbName = "video-editor-media-fallback";

	private async getFallbackDB(): Promise<IDBDatabase> {
		return new Promise((resolve, reject) => {
			const request = indexedDB.open(OPFSAdapter.fallbackDbName, 1);
			request.onerror = () => reject(request.error);
			request.onsuccess = () => resolve(request.result);
			request.onupgradeneeded = () => {
				const db = request.result;
				if (!db.objectStoreNames.contains("files")) {
					db.createObjectStore("files", { keyPath: "id" });
				}
			};
		});
	}

	private async fallbackGet(key: string): Promise<File | null> {
		const db = await this.getFallbackDB();
		return new Promise((resolve, reject) => {
			const request = db.transaction("files", "readonly").objectStore("files").get(this.fallbackKey(key));
			request.onerror = () => reject(request.error);
			request.onsuccess = () => {
				const value = request.result?.file as Blob | undefined;
				resolve(value ? new File([value], key, { type: value.type, lastModified: Date.now() }) : null);
			};
		});
	}

	private async fallbackSet(key: string, file: File): Promise<void> {
		const db = await this.getFallbackDB();
		await new Promise<void>((resolve, reject) => {
			const request = db.transaction("files", "readwrite").objectStore("files").put({ id: this.fallbackKey(key), file });
			request.onerror = () => reject(request.error);
			request.onsuccess = () => resolve();
		});
	}

	private async fallbackRemove(key: string): Promise<void> {
		const db = await this.getFallbackDB();
		await new Promise<void>((resolve, reject) => {
			const request = db.transaction("files", "readwrite").objectStore("files").delete(this.fallbackKey(key));
			request.onerror = () => reject(request.error);
			request.onsuccess = () => resolve();
		});
	}

	private async fallbackList(): Promise<string[]> {
		const db = await this.getFallbackDB();
		return new Promise((resolve, reject) => {
			const request = db.transaction("files", "readonly").objectStore("files").getAllKeys();
			request.onerror = () => reject(request.error);
			request.onsuccess = () => resolve((request.result as string[]).filter((id) => id.startsWith(`${this.directoryName}:`)).map((id) => id.slice(this.directoryName.length + 1)));
		});
	}

	private async fallbackClear(): Promise<void> {
		for (const key of await this.fallbackList()) await this.fallbackRemove(key);
	}

	private fallbackKey(key: string): string {
		return `${this.directoryName}:${key}`;
	}

	constructor(directoryName = "media") {
		this.directoryName = directoryName;
	}

	private async getDirectory(): Promise<FileSystemDirectoryHandle> {
		const opfsRoot = await navigator.storage.getDirectory();
		return await opfsRoot.getDirectoryHandle(this.directoryName, {
			create: true,
		});
	}

	async get(key: string): Promise<File | null> {
		if (!OPFSAdapter.isSupported()) return this.fallbackGet(key);
		try {
			const directory = await this.getDirectory();
			const fileHandle = await directory.getFileHandle(key);
			return await fileHandle.getFile();
		} catch (error) {
			if ((error as Error).name === "NotFoundError") {
				return null;
			}
			throw error;
		}
	}

	async set(key: string, file: File): Promise<void> {
		if (!OPFSAdapter.isSupported()) return this.fallbackSet(key, file);
		const directory = await this.getDirectory();
		const fileHandle = await directory.getFileHandle(key, { create: true });
		const writable = await fileHandle.createWritable();

		await writable.write(file);
		await writable.close();
	}

	async remove(key: string): Promise<void> {
		if (!OPFSAdapter.isSupported()) return this.fallbackRemove(key);
		try {
			const directory = await this.getDirectory();
			await directory.removeEntry(key);
		} catch (error) {
			if ((error as Error).name !== "NotFoundError") {
				throw error;
			}
		}
	}

	async list(): Promise<string[]> {
		if (!OPFSAdapter.isSupported()) return this.fallbackList();
		const directory = await this.getDirectory();
		const keys: string[] = [];

		for await (const name of directory.keys()) {
			keys.push(name);
		}

		return keys;
	}

	async clear(): Promise<void> {
		if (!OPFSAdapter.isSupported()) return this.fallbackClear();
		const directory = await this.getDirectory();

		for await (const name of directory.keys()) {
			await directory.removeEntry(name);
		}
	}

	// Helper method to check OPFS support
	static isSupported(): boolean {
		return typeof navigator !== "undefined" && !!navigator.storage && typeof navigator.storage.getDirectory === "function";
	}
}
