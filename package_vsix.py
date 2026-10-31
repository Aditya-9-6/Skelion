import os
import zipfile

ROOT = r"C:\Users\adity\.gemini\antigravity\brain\5b2cce19-829f-47e8-a475-c50d0b5847f8\skelion_vscode_extension"
OUT_VSIX = os.path.join(ROOT, "skelion-vscode-0.1.0.vsix")
DEST_VSIX = r"g:\My Drive\helios\skelion_vscode_extension\skelion-vscode-0.1.0.vsix"


def build_vsix():
    print(f"Building VSIX from {ROOT} -> {OUT_VSIX}...")

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
    <Identity Id="skelion-vscode" Version="0.1.0" Language="en-US" Publisher="AdityaDnyaneshwarDahale" />
    <DisplayName>Skelion Agent</DisplayName>
    <Description xml:space="preserve">VS Code panel for Skelion authentication &amp; billing</Description>
    <Tags>AI,DevOps,Incident</Tags>
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
            full_src = os.path.join(ROOT, src)
            if os.path.exists(full_src):
                z.write(full_src, dest)
                print(f"Packed: {src} -> {dest}")
            else:
                print(f"Warning: Missing {full_src}")

    # Copy to helios folder
    import shutil

    shutil.copyfile(OUT_VSIX, DEST_VSIX)
    print(f"VSIX built and copied to {DEST_VSIX}")
    print(f"Size: {os.path.getsize(OUT_VSIX)} bytes")


if __name__ == "__main__":
    build_vsix()
