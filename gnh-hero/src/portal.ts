import '@fontsource/space-grotesk/700.css'
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import './style.css'
import './gateway.css'

import { runCurtain } from './curtain'
import { fillStrings, enterGateway, initDoors } from './gateway'

/** Flag para ligar/desligar a cortina de abertura. */
const RUN_CURTAIN = true

const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
const curtain = document.querySelector<HTMLElement>('.gw-curtain')!

fillStrings()
initDoors(reduced)

// cortina em toda carga da página (inclusive reload)
async function boot(): Promise<void> {
  if (RUN_CURTAIN && !reduced) {
    await runCurtain(curtain)
  } else {
    curtain.style.display = 'none'
  }
  enterGateway(reduced)
}

void boot()
