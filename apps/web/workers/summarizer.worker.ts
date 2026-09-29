import { WebWorkerMLCEngineHandler } from "@mlc-ai/web-llm"

/**
 * WebGPU inference worker. The main thread creates a WebWorkerMLCEngine pointing at this file;
 * the handler forwards requests here so model loading and generation stay off the main thread.
 */

const handler = new WebWorkerMLCEngineHandler()

self.onmessage = (message: MessageEvent) => {
    handler.onmessage(message)
}
