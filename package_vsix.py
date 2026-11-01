import os
import zipfile
import shutil

SRC_DIR = r"g:\My Drive\helios\skelion_vscode_extension"
BRAIN_DIR = r"C:\Users\adity\.gemini\antigravity\brain\5b2cce19-829f-47e8-a475-c50d0b5847f8\skelion_vscode_extension"
OUT_VSIX = os.path.join(SRC_DIR, "skelion-vscode-0.1.0.vsix")
BRAIN_VSIX = os.path.join(BRAIN_DIR, "skelion-vscode-0.1.0.vsix")


def build_vsix():
    print(f"Building VSIX from {SRC_DIR} -> {OUT_VSIX}...")
    os.makedirs(BRAIN_DIR, exist_ok=True)
    os.makedirs(os.path.join(BRAIN_DIR, "out"), exist_ok=True)

    # Sync compiled outputs to brain directory as artifacts
    for f in ["out/extension.js", "out/extension.js.map", "package.json"]:
        src_f = os.path.join(SRC_DIR, f)
        brain_f = os.path.join(BRAIN_DIR, f)
        if os.path.exists(src_f):
            shutil.copyfile(src_f, brain_f)

    # Files to include in the extension/ folder
    files_to_pack = [
        ("package.json", "extension/package.json"),
        ("out/extension.js", "extension/out/extension.js"),
        ("out/extension.js.map", "extension/out/extension.js.map"),
        ("media/icon.svg", "extension/media/icon.svg"),
    ]

    # Content types XML
    content_types = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json" />
  <Default Extension="js" ContentType="application/javascript" />
  <Default Extension="svg" ContentType="image/svg+xml" />
  <Default Extension="map" ContentType="application/json" />
  <Default Extension="vsixmanifest" ContentType="text/xml" />
</Types>"""

    # Manifest XML
    manifest = """<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
  <Metadata>
    <Identity Id="skelion-vscode" Version="0.1.0" Language="en-US" Publisher="adity" />
    <DisplayName>Skelion Agent</DisplayName>
    <Description xml:space="preserve">VS Code panel for Skelion authentication &amp; billing with Autonomous DevOps Loop</Description>
    <Tags>AI,DevOps,Incident,AutonomousLoop</Tags>
    <Categories>AI,Other</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Icon>extension/media/icon.svg</Icon>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.88.0" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value="" />
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
  </Assets>
</PackageManifest>"""

    with zipfile.ZipFile(OUT_VSIX, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("extension.vsixmanifest", manifest)

        for src, dest in files_to_pack:
            full_src = os.path.join(SRC_DIR, src)
            if os.path.exists(full_src):
                z.write(full_src, dest)
                print(f"Packed: {src} -> {dest}")
            else:
                print(f"Warning: Missing {full_src}")

    shutil.copyfile(OUT_VSIX, BRAIN_VSIX)
    print(f"VSIX built and copied to {BRAIN_VSIX}")
    print(f"Size: {os.path.getsize(OUT_VSIX)} bytes")


if __name__ == "__main__":
    build_vsix()
