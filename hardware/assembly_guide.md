# Nexo Assembly Guide

This guide details the process of printing, building, and wiring the Nexo Smart Speaker.

## Safety Warning

- **Mains Voltage:** This project uses an industrial power supply (110V/220V).
- **Chemicals:** When mixing Plaster and PVA, wear gloves and work in a ventilated area.
- **Wood working:** When cutting/sanding/milling the wooden parts, wear safety glasses and watch out for your hands.

---

## Phase 1: The Enclosure

### 1. 3D Printing

All parts were printed in **PETG** for durability and heat resistance.

- **Walls:** 2 perimeters (minimum).
- **Infill:** 15% Rectilinear (except for the subwoofer walls which are hollow for filling).

All printing parameters should be set to your specific printer. I personally printed everything on more filament and time saving settings and everything turned out great, so as long as you know which settings get you a decent quality print, I wouldn't be too worried about settings.

> **Note on Material:** PETG is completely fine to use, however using PCTG might be beneficial because of the higher temperature resistance (though in tests, it looks like it's not much different from PETG).

### 2. The Composite Fill (Subwoofer)

To give the subwoofer weight and acoustic density:

1.  Prepare a mixture of **90% Plaster of Paris** and **10% PVA Glue** (White wood glue).
2.  Add a small amount of water until it reaches a "pourable pancake batter" consistency if too viscous.
3.  Pour the mixture into the hollow cavities of the 3D-printed subwoofer shell.
4.  **Let it cure for at least 48 hours.** The PVA slows down the drying process but prevents the plaster from cracking. Also make sure it's in a well ventilated and/or heated area, so that it's not wet.
5.  Once it's all set, put some cotton wool (or polyfil) inside the enclosure, to help with bass response and make the enclosure feel "bigger" than it actually is.

<img height="300" alt="image" src="https://github.com/user-attachments/assets/a50ba928-1fcf-4eff-88a3-3b3355b80033" />


### 3. Woodworking

The outer shell utilizes a wooden board for aesthetics and extra rigidity.

The wooden board uses a kerf bending method to bend the sides of the board according to the circular edges of the speaker enclosure. Make sure to cut the kerf cuts accordingly.

- Cut the board to size according to the following template including the kerf cuts.
- Use a router (or a Forstner bit) to carve out spaces for the buttons and LEDs.
- Sand up to 400 grit and apply oil/stain before final assembly.
- Bend (and glue the kerf cuts) the upper half of the board so that it fits the upper half of the speaker, leave the bottom straight so the speaker can be easily wrapped around with the wood.
- Finally varnish and color (if wanted) the wood enclosure to fit your needs.

This part can definitely also be 3D printed out of PETG, which was initially planned anyways. I just thought wood might look better plus it saved like 600 grams of plastic.

<img height="300" alt="image" src="https://github.com/user-attachments/assets/7238f69f-06e1-48ed-ba6e-8845b81bbfbd" />

### Other Tasks

- Put a silicon ring around the holes for the subwoofer speaker and passive radiator to get a good seal on the enclosure. Caulk can be used for this.
- Glue everything needed together. (Such as the parts of the subwoofer enclosure, mounting rings to the enclosure).
- Paint and/or polish the look of the front and back plates. You can use wood filler to make it look more matte and less like plastic.
- Screw components into their specific holders.
- place the C14 plug and switch into its holes on the back plate, wire everything up.
- Screw the amplifier onto the inner side of the back plate and connect everything up correctly to it (the right channel to the woofer, the left channel to all the other speakers), the tweeters should be conneted through the high pass filter.

---

## Phase 2: Electronics & Wiring

### 1. Wiring Diagram

Below is a _(very professional)_ connection map of the Raspberry Pi and small electronics:

<img height="300" alt="wiring diagram" src="https://github.com/user-attachments/assets/69685e06-cedf-429e-ba09-ace04cc23731" />

- The LEDs and buttons are connected to a common ground coming from the RPi (the buttons connections depend on your specific buttons, mine required 5V, GND and had a signal OUT).
- Each LED is independently connected to the specific used pins to the RPi, every LED also has a resistor before connecting to the ground.
- Each button signal output is also connected to the RPi so that we know when it was pressed.
- Finally, the optocoupler is connected to its own pin and ground which then is able to control the muting of the amplifier using just a simple LOW/HIGH signal from the RPi.

### 2. Power System

- **Amp Power:** Connect the Mean Well 36V PSU output to the TPA3255 amp input using **14 AWG** silicone wire.
- **RPi Power:** Run the official USB-C power supply to the Pi 5.
  > Or you can power the RPi using the internal psu using an isolated DC-DC converter or by then using a ground loop isolator on the audio output of the RPi.

### 3. The Mute Circuit

Since the SAMP-100 TPA3255 amp board supports hardware muting, I implemented an optocoupler circuit to let the Pi mute the amp to prevent unnecessary electrical noise when no music is playing.

- **Optocoupler:** Panasonic AQY212EHAT.
- **Connection:**
  - _Input Side:_ GPIO 26 (RPi) -> Resistor -> Optocoupler LED -> GND (RPi).
  - _Output Side:_ Connects the Amp's MUTE and GND pins, polarity on this specific optocoupler and amp doesn't matter.

---

## Phase 3: Final Assembly

1.  **Mounting Drivers:** Screw the woofer and tweeters into the front plate.
2.  **Mounting Electronics:** Screw the electronic components in their mounting holders onto the enclosure.
3.  **Closing the Box:** Screw the subwoofer speaker and passive radiator very tightly into the subwoofer enclosure to ensure an airtight seal.
4.  **Wrap the rest using the bendable wood:** Enclose the whole speaker in the wood. Make sure the bottom part of the wooden board holds nicely, glue the bottom part down properly and let it sit for a while.

The whole speaker should be finished now.

---

## What I would do differently

Here are things I would change in a future build. You might want to consider these before you build yours:

### 1. Threaded Inserts

In this version, I screwed directly into the plastic and/or used nuts held in place by friction and super glue.

- Use **Heat-Set Inserts (M3/M4)** for every screw point. Redesign the 3D files to accommodate them.
- This will overall fix mounting issues and might help seal the subwoofer enclosure airtight a bit more.

### 2. Power Supply Integration

Having two power plugs (one for Amp, one for Pi) is clunky.

- Find an isolated DC-DC converter that actually works without ground loops, or build a custom linear power supply stage to feed 5V from the 36V rail cleanly.
  > Or just use a ground loop isolator at the RCA DAC connections (might hurt audio quality).

### 3. Ease of opening

Currently, removing the wooden is practically impossible, because it's glued down to the actual speaker enclosure.

- It would be a lot better to make some mounting plates sticking out of the wood to properly mount the back and front plates, so that it can be removed properly.
- Also placing all of the back plate mounted components onto the enclosure might help too, because the back plate would be removable a bit better, however it still has all the mains power on it, which is still a big issue.

> These are all quality of life improvements, that physically don't need to be there for it to work really good, but they could be good to have in the long term. For me though, they don't really cause issues for now.

---

## All .stl files for 3D printing are available in the `/files` directory.

- All CAD was designed in OnShape and the direct link to the CAD so you can clone it and edit parts directly is [**here**](https://cad.onshape.com/documents/64120ed53810ec4d5c769f33/w/fbffd58ca4d500f12472e03c/e/86b9a890bc291adbebea1ccb?renderMode=0&uiState=698ede0bcd522a852c22394d)
