/**
 * Native Marathi speech services for Kisan Mitra.
 *
 * Speech-to-Text and Text-to-Speech use device-native APIs only:
 * - Android: SpeechRecognizer / TextToSpeech
 * - iOS: SFSpeechRecognizer / AVSpeechSynthesizer
 *
 * No cloud speech API is used. When Marathi recognition is unavailable
 * (common on iOS), callers receive a graceful typed-input fallback.
 */

import { NativeModules, Platform, PermissionsAndroid } from 'react-native';

export type SpeechAvailability = {
  sttAvailable: boolean;
  ttsAvailable: boolean;
  marathiSttSupported: boolean;
  marathiTtsVoicePresent: boolean;
  fallbackReason: string | null;
};

export type ListenResult = {
  transcript: string;
  isFinal: boolean;
  editedByUser: boolean;
};

export type SpeechError = {
  code:
    | 'permission_denied'
    | 'unavailable'
    | 'language_unsupported'
    | 'timeout'
    | 'network'
    | 'unknown';
  message: string;
  recoverable: boolean;
};

const MARATHI_LOCALE = 'mr-IN';
const LISTEN_TIMEOUT_MS = 30000;

const NativeSpeech: any = NativeModules.KisanSpeech;

function ensureNativeModule(): void {
  if (!NativeSpeech) {
    throw {
      code: 'unavailable',
      message: 'Native speech module is not linked.',
      recoverable: true,
    } as SpeechError;
  }
}

export async function requestPermissions(): Promise<boolean> {
  if (Platform.OS === 'android') {
    const granted = await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
      {
        title: 'माइक्रोफोन परवानगी',
        message: 'आवाजाने प्रश्न विचारण्यासाठी माइक्रोफोन आवश्यक आहे.',
        buttonPositive: 'परवानगी द्या',
        buttonNegative: 'रद्द करा',
      }
    );
    return granted === PermissionsAndroid.RESULTS.GRANTED;
  }
  ensureNativeModule();
  return NativeSpeech.requestPermissions();
}

export async function getSpeechAvailability(): Promise<SpeechAvailability> {
  const base: SpeechAvailability = {
    sttAvailable: false,
    ttsAvailable: false,
    marathiSttSupported: false,
    marathiTtsVoicePresent: false,
    fallbackReason: null,
  };

  try {
    ensureNativeModule();
    const status = await NativeSpeech.checkAvailability(MARATHI_LOCALE);
    return {
      sttAvailable: Boolean(status.sttAvailable),
      ttsAvailable: Boolean(status.ttsAvailable),
      marathiSttSupported: Boolean(status.marathiSttSupported),
      marathiTtsVoicePresent: Boolean(status.marathiTtsVoicePresent),
      fallbackReason: status.fallbackReason ?? null,
    };
  } catch (error) {
    return {
      ...base,
      fallbackReason:
        error instanceof Error ? error.message : 'Speech service unavailable.',
    };
  }
}

export async function startListening(
  onPartial: (text: string) => void
): Promise<ListenResult> {
  ensureNativeModule();
  const permitted = await requestPermissions();
  if (!permitted) {
    throw {
      code: 'permission_denied',
      message: 'माइक्रोफोन परवानगी नाकारली गेली.',
      recoverable: true,
    } as SpeechError;
  }

  const availability = await getSpeechAvailability();
  if (!availability.sttAvailable || !availability.marathiSttSupported) {
    throw {
      code: 'language_unsupported',
      message: 'या उपकरणावर मराठी ओळख उपलब्ध नाही. कृपया लिहून विचारा.',
      recoverable: true,
    } as SpeechError;
  }

  return new Promise<ListenResult>((resolve, reject) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      NativeSpeech.stopListening();
      reject({
        code: 'timeout',
        message: 'आवाज ओळखण्यास कालबाह्य झाले. कृपया पुन्हा प्रयत्न करा.',
        recoverable: true,
      } as SpeechError);
    }, LISTEN_TIMEOUT_MS);

    const cleanup = () => {
      clearTimeout(timer);
      NativeSpeech.removeAllListeners?.();
    };

    const partialSub = NativeSpeech.addListener?.('onSpeechPartial', (text: string) => {
      onPartial(text);
    });

    const resultSub = NativeSpeech.addListener?.(
      'onSpeechResult',
      (text: string) => {
        if (settled) return;
        settled = true;
        cleanup();
        partialSub?.remove?.();
        resultSub?.remove?.();
        errorSub?.remove?.();
        resolve({ transcript: text ?? '', isFinal: true, editedByUser: false });
      }
    );

    const errorSub = NativeSpeech.addListener?.('onSpeechError', (err: any) => {
      if (settled) return;
      settled = true;
      cleanup();
      partialSub?.remove?.();
      resultSub?.remove?.();
      errorSub?.remove?.();
      reject({
        code: err?.code ?? 'unknown',
        message: err?.message ?? 'आवाज ओळखण्यात त्रुटी झाली.',
        recoverable: err?.code !== 'permission_denied',
      } as SpeechError);
    });

    NativeSpeech.startListening(MARATHI_LOCALE).catch((error: any) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject({
        code: 'unavailable',
        message: error?.message ?? 'आवाज सेवा उपलब्ध नाही.',
        recoverable: true,
      } as SpeechError);
    });
  });
}

export async function stopListening(): Promise<void> {
  ensureNativeModule();
  await NativeSpeech.stopListening();
}

export type SpeakOptions = {
  pitch?: number;
  rate?: number;
  onDone?: () => void;
  onError?: (error: SpeechError) => void;
};

export async function speak(text: string, options: SpeakOptions = {}): Promise<void> {
  const trimmed = (text ?? '').trim();
  if (!trimmed) {
    options.onError?.({
      code: 'unknown',
      message: 'बोलण्यासाठी मजकूर नाही.',
      recoverable: true,
    });
    return;
  }

  try {
    ensureNativeModule();
    const availability = await getSpeechAvailability();
    if (!availability.ttsAvailable || !availability.marathiTtsVoicePresent) {
      options.onError?.({
        code: 'language_unsupported',
        message: 'या उपकरणावर मराठी आवाज उपलब्ध नाही. कृपया मजकूर वाचा.',
        recoverable: true,
      });
      return;
    }
    await NativeSpeech.speak(trimmed, {
      locale: MARATHI_LOCALE,
      pitch: options.pitch ?? 1.0,
      rate: options.rate ?? 0.9,
    });
    options.onDone?.();
  } catch (error) {
    options.onError?.({
      code: 'unavailable',
      message: error instanceof Error ? error.message : 'TTS अनुपलब्ध.',
      recoverable: true,
    });
  }
}

export async function stopSpeaking(): Promise<void> {
  try {
    ensureNativeModule();
    await NativeSpeech.stopSpeaking();
  } catch {
    // no-op: stopping an idle synthesizer is safe to ignore
  }
}

export function markEdited(result: ListenResult, newText: string): ListenResult {
  return { ...result, transcript: newText, editedByUser: true };
}
