# Monolithic Source Code (Original Version)

This directory contains the original, unmodularized version of the source code for the SDN-based vehicular communication framework.

## Purpose

The files in this folder represent the **initial all-in-one implementation** before any modular refactoring or packaging. They are preserved here for reference, debugging, or backward compatibility purposes.

## Warning

> ⚠️ **Note**: This version is not intended for production or scalable use. Please refer to the main project folder for the fully modularized and maintainable version of the code.

## Included Files

- `controller.py` – Central SDN controller managing flow rules and interface switching logic.
- `node_client.py` – Node logic with interface monitoring, switching, and data forwarding.
- `switch_tech.py` – Technology switching interface for ITS-G5 and CV2X.
- `wifi_p2p_server.py` – Group Owner (GO) script for Wi-Fi Direct forwarding.
- `wifi_p2p_client.py` – Client script for Wi-Fi Direct forwarding.

## Recommendation

For clean, scalable, and maintainable development, use the modular version located in the main project structure.
