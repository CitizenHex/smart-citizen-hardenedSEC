## 0.6.x Dependency Internalization
- removed dependencies on external ini sources 
- started adding item stat enhancements 

## 0.7.x Final Ship, Gear, Item & Journal Detail Enhancements & App Rearchitecture
- remove data folder dependency so all enhancements are dynamically generated
- rename overrides.ini to user.ini
- change config so that users can import any external ini that will be used to update user.ini
- complete enhancements for ships, gear, components and journal items
- configurable enhancements
- useful info added to journal such as crafting/mining information
- end-to-end testing & version release

### 0.7.0 Hotfixes
- fix crash when install dir not found

### 0.7.1 Fixes
- remember install locations from previous installs when installing/upgrading a new version
- grouped sort not working with commodities 
- Hemera is not getting its labels 
- fix missing blueprints

## 0.8.x Final Mission, Crafting, & Commodity Detail Enhancements
- complete enhancements & fixes for missions
- complete enhancements & fixes for crafting
- complete enhancements & fixes for commodity details
-stability & bugfixes
-end-to-end testing & version release

## 0.9.x
-pre-release final polish
-stability & bugfixes
-performance optimization
-cache streamlining
-end-to-end testing & version release


This File lists all the remaining objectives as of the release of v0.5.3 on the road to 1.0 release:

# Further enrich contract details
* add reputation/xp to contract title or description

# Further Enrich commodity information
* for commodities used in blueprints, list every blueprint a commodity is involved in
* possibly include how much of the commodity is used for each blueprint
* Add scan signatures to commodity info 

# Journal Enhancements
* Improve existing journal content 
* Leverage lame journal content and replace with useful content
* Scan signature table in journal

# Starmap Info
* Can we get the asteroid clusters info to show what mineables are there in the same way planets show it?
* For planets listing minerals, add scan signatures and what blueprints are used for them


# Other

* user.cfg localization string setup