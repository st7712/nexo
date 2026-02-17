# Nexo Hardware Overview

This directory contains all the documentation regarding the physical construction, wiring, and component selection for the Nexo Smart Speaker.

Unlike standard 3D-printed speakers, Nexo aims for high-density acoustic properties by combining 3D printing, wood, and composite materials.

<div align="center">
  <img src="https://placehold.co/600x400?text=Nexo+Hardware+Overview" alt="Nexo Hardware" width="50%">
</div>

## Documentation

- **[Bill of Materials (BOM)](https://github.com/st7712/nexo/blob/main/hardware/bom.md)** - Full parts list, costs, and purchase links.
- **[Assembly Guide](https://github.com/st7712/nexo/blob/main/hardware/assembly_guide.md)** - Step-by-step tutorial on building the enclosure and wiring.

---

## Design Philosophy & Component Selection

### 1. The Subwoofer Enclosure (Plaster + PVA)

One of the biggest issues with DIY 3D printed speakers is that plastic is light and resonates easily, which makes the bass muddy.

- The subwoofer enclosure walls are designed with hollow cavities.
- I filled these cavities with a mixture of **Plaster of Paris**. Plaster of Paris and water is mixed using a 1:1 ratio, the **PVA glue** is then mixed with about an 1:10 ratio with the Plaster of Paris. I recommend trying out exact ratios yourself though.
- The PVA makes the plaster less brittle and significantly denser. This creates a "dead" cabinet that doesn't vibrate, resulting in much cleaner low-end frequencies.

### 2. The Amplifier (TPA3255)

I originally looked at standard TPA3116D2 boards, but settled on the **TPA3255 (SAMP-100)**.

- It has significantly cleaner power delivery, has **zero "thump" noise** when powering on or off. It also is very powerful and should handle pretty much anything. Lastly it was actually pretty cheap because I was purchasing it used.

### 3. The Brain (Raspberry Pi 5)

I used a Raspberry Pi 5 (4GB).

- **It's very overkill.** A Pi 3B+ or 4 would work fine. Any basic RPi that can run Linux will work.
- I wanted to get a powerful RPi that I will be able to use for my other personal usecases too, as well as future learning with microcontrollers. Another reason was the fact that the Pi 4 wasn't much cheaper than the 5, so I went for it.

---

## Challenges & Problems Encountered

### Ground loops

Originally, I planned to power everything from the single 36V Mean Well power supply, using a cheap DC-DC buck converter to step down 36V -> 5V for the Raspberry Pi.

This created a massive ground loop. The shared ground between the Amp and the Pi (via the buck converter) introduced audible whining and screeching noise into the audio signal. The music playback was unusable and you couldn't hear anything other than the loud screech.

I removed the buck converter entirely. The final build uses:

1.  **Mean Well 36V PSU** -> Powering ONLY the Amplifier.
2.  **Official Raspberry Pi PSU** -> Powering the Raspberry Pi.
    _This isolates the power grounds and results in a completely silent noise floor._

This also brings a benefit of being able to have the RPi running 24/7 without any coil whine, because the RPi PSU is silent.
However it does add another cable that goes to the speaker, which might make it look clunky.

If you prefer a single cable installation, I recommend getting either an isolated DC-DC converter, or an RCA (or AUX) ground loop isolator, which will effectively remove the ground loop, however the isolated DC-DC converter is expensive, and the RCA isolator might reduce audio quality.

Another internal PSU (like the RPi PSU) can be also actually placed inside of the enclosure and be wired up to the C14 connector, effectively using just one cable, however that would require more inside space, which I couldn't afford.

### Not ideal CAD design

There were a few issues when assembling the enclosure together.
The main issue was the lack of heat inserts or at least somewhat inserted screw nuts in the design, later requiring the manufacturing of special screw rings, that properly hold the speakers.

---

## 🖼️ Gallery

<div align="center">
  <img src="https://placehold.co/400x300?text=Wiring+Diagram" alt="Wiring" width="45%">
  <img src="https://placehold.co/400x300?text=Printed+Parts" alt="Parts" width="45%">
</div>
