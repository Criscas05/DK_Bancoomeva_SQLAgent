// static/recorder-worklet.js
// Convierte Float32 → Int16 y envía al puerto del nodo.
class RecorderProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0][0]; // mono
    if (!input) return true;

    const int16 = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
      let s = Math.max(-1, Math.min(1, input[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }

    this.port.postMessage(int16.buffer, [int16.buffer]); // transf. ownership
    return true;
  }
}

registerProcessor("recorder-processor", RecorderProcessor);
