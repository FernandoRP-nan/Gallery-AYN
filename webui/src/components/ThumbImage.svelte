<script lang="ts">
  import { galleryThumbHqFor, galleryThumbHqCacheRevision } from "../lib/galleryThumbHqCache";

  /** Miniatura con capas LQ→HQ estilo Google Photos: la LQ permanece hasta que la HQ decodifica. */
  export let itemPath = "";
  export let thumbDataUrl: string;
  export let thumbQuality: "lq" | "hq" | undefined = undefined;
  export let thumbLqDataUrl: string | null | undefined = null;
  export let freezeTransitions = false;

  let hqDecoded = false;
  let trackedHqUrl = "";

  let hqPathStore: ReturnType<typeof galleryThumbHqFor> | null = null;

  $: cacheRevision = $galleryThumbHqCacheRevision;
  $: {
    void cacheRevision;
    hqPathStore = itemPath ? galleryThumbHqFor(itemPath) : null;
  }
  $: cached = hqPathStore ? $hqPathStore : null;

  $: hqUrl = cached?.hqUrl ?? (thumbQuality === "hq" ? thumbDataUrl : null);
  $: lqUrl =
    cached?.lqUrl ??
    thumbLqDataUrl ??
    (thumbQuality === "lq" ? thumbDataUrl : null);
  /** Sin placeholder LQ: mostrar HQ de inmediato (p. ej. caché del servidor). */
  $: if (hqUrl && !lqUrl) {
    hqDecoded = true;
  }

  $: if (hqUrl !== trackedHqUrl) {
    trackedHqUrl = hqUrl ?? "";
    hqDecoded = Boolean(hqUrl && !lqUrl);
  }

  function onHqLoad() {
    hqDecoded = true;
  }
</script>

<div
  class="thumb-stack"
  class:thumb-stack--freeze={freezeTransitions}
  class:thumb-stack--hq-ready={hqDecoded && Boolean(hqUrl)}
>
  {#if lqUrl && (!hqUrl || !hqDecoded)}
    <img
      class="thumb-stack__lq"
      src={lqUrl}
      alt=""
      draggable={false}
      loading="eager"
      decoding="async"
    />
  {/if}
  {#if hqUrl}
    <img
      class="thumb-stack__hq"
      class:thumb-stack__hq--visible={hqDecoded}
      src={hqUrl}
      alt=""
      draggable={false}
      loading="eager"
      decoding="async"
      on:load={onHqLoad}
    />
  {/if}
</div>
