let
  sources = import ./nix/sources.nix;
  pkgs = import sources.nixpkgs {};
in
pkgs.mkShell {
  name = "rawfile-shell";

  buildInputs = with pkgs; [
    kubectl
    kubernetes-helm-wrapped
    helm-docs
    nixos-shell
    kind
    python313
    poetry # Python3.13 is not supported (Overriding python3 input will not work)
    gcc
    gnumake
    btrfs-progs
    stdenv.cc.cc.lib
  ] ++ pkgs.lib.optional (builtins.getEnv "IN_NIX_SHELL" == "pure") [ docker-client ];
  shellHook = ''
    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib"
    poetry install
    source $(poetry env info -p)/bin/activate
  '';
  postShellHook = ''
    deactivate
  '';
}

