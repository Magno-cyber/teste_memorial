/**
 * Aba Colegas (Sala 06): busca de ex-alunos e perfil, alimentados pelos check-ins.
 * A busca é feita no servidor (hook useAlunos, chamado em SalaConteudo); sem rede, a tela mantém
 * o último resultado e avisa no rodapé.
 */
import type { EstadoBusca } from '../dados/alunos';
import type { RespostaSala } from '../dados/tipos';
import { Busca } from './Busca';
import type { PropsSala } from './estado';
import { Perfil } from './Perfil';

interface Props extends PropsSala {
  dados: RespostaSala;
  busca: EstadoBusca;
}

export function Colegas({ estado: st, mudar, dados, busca }: Props) {
  if (st.visao === 'perfil' && st.perfilId !== null) {
    return (
      <Perfil
        key={st.perfilId}
        id={st.perfilId}
        aba={st.perfilAba}
        aoMudarAba={(perfilAba) => mudar({ perfilAba })}
        aoVoltar={() => mudar({ visao: 'busca', perfilId: null, perfilAba: 'geral' })}
        aoAbrir={(id) => mudar({ perfilId: id, perfilAba: 'geral' })}
      />
    );
  }
  return (
    <Busca
      sala={dados.sala}
      estado={st}
      mudar={mudar}
      busca={busca}
      anoInicial={dados.config.anoInicial}
      aoCheckin={() => mudar({ overlay: { tipo: 'checkin' }, teclado: false })}
    />
  );
}
